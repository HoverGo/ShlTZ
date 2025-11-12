from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional
from urllib.parse import urlparse

import pandas as pd
import requests
from cacheops import cached
from django.conf import settings
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from .models import Item

logger = logging.getLogger('items.importer')

REQUIRED_COLUMNS = {'name', 'category', 'price', 'updated_at'}
COLUMN_ALIASES = {
    'product_name': 'name',
    'item_name': 'name',
    'title': 'name',
    'category_name': 'category',
    'group': 'category',
    'price_usd': 'price',
    'amount': 'price',
    'value': 'price',
    'updated': 'updated_at',
    'updated_on': 'updated_at',
    'last_updated': 'updated_at',
    'timestamp': 'updated_at',
    'modified_at': 'updated_at',
    'id': 'source_id',
    'item_id': 'source_id',
    'sku': 'source_id',
    'external_id': 'source_id',
}


@dataclass
class ImportReport:
    created: int
    updated: int
    total_rows: int


def _read_remote_content(source_url: str) -> pd.DataFrame:
    logger.info('Fetching data from %s', source_url)
    response = requests.get(source_url, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get('Content-Type', '')
    parsed = urlparse(source_url)
    if 'json' in content_type or parsed.path.endswith('.json'):
        return pd.read_json(io.BytesIO(response.content))
    return pd.read_csv(io.BytesIO(response.content))


def _read_local_sample(path: str) -> pd.DataFrame:
    logger.info('Loading fallback data from %s', path)
    if path.endswith('.json'):
        return pd.read_json(path)
    return pd.read_csv(path)


def load_raw_dataframe(source_url: Optional[str] = None) -> pd.DataFrame:
    """
    Load data into a pandas DataFrame.
    """
    source_url = source_url or settings.IMPORT_SOURCE_URL
    if source_url:
        try:
            return _read_remote_content(source_url)
        except requests.RequestException as exc:
            logger.warning('Remote load failed (%s); falling back to local sample.', exc)
    return _read_local_sample(settings.LOCAL_SAMPLE_DATA_PATH)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize arbitrary dataframe columns into the expected schema.
    """
    if df.empty:
        return df

    df = df.copy()
    df.columns = [column.strip().lower() for column in df.columns]
    df.rename(columns={col: COLUMN_ALIASES.get(col, col) for col in df.columns}, inplace=True)

    # Fill missing required columns with NaN placeholders
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    # Select columns that exist
    columns_to_select = list(REQUIRED_COLUMNS)
    if 'source_id' in df.columns:
        columns_to_select.append('source_id')
    df = df[columns_to_select]

    df['name'] = df['name'].astype(str).str.strip()
    df['category'] = df['category'].astype(str).str.strip()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['updated_at'] = pd.to_datetime(df['updated_at'], utc=True, errors='coerce')

    df.dropna(subset=['name', 'category', 'price', 'updated_at'], inplace=True)

    if 'source_id' in df.columns:
        df['source_id'] = df['source_id'].where(df['source_id'].notna(), None)
        df['source_id'] = df['source_id'].apply(lambda value: str(value).strip() if value is not None else None)
    else:
        df['source_id'] = None

    def _compute_source_uid(row: pd.Series) -> str:
        base = row['source_id'] or f"{row['name']}|{row['category']}"
        digest = hashlib.sha1(base.encode('utf-8')).hexdigest()
        return digest

    df['source_uid'] = df.apply(_compute_source_uid, axis=1)
    df['price'] = df['price'].apply(
        lambda value: Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    )

    return df[['source_uid', 'name', 'category', 'price', 'updated_at']]


def upsert_items(normalized_df: pd.DataFrame) -> ImportReport:
    if normalized_df.empty:
        return ImportReport(created=0, updated=0, total_rows=0)

    created = 0
    updated = 0

    with transaction.atomic():
        records: Iterable[dict] = normalized_df.to_dict(orient='records')
        for record in records:
            updated_at = record['updated_at']
            if isinstance(updated_at, pd.Timestamp):
                updated_at = updated_at.to_pydatetime()
            if timezone.is_naive(updated_at):
                updated_at = timezone.make_aware(updated_at, timezone=timezone.utc)

            obj, created_flag = Item.objects.update_or_create(
                source_uid=record['source_uid'],
                defaults={
                    'name': record['name'],
                    'category': record['category'],
                    'price': record['price'],
                    'updated_at': updated_at,
                },
            )
            if created_flag:
                created += 1
            else:
                updated += 1

    logger.info('Import completed: %s created, %s updated (rows processed: %s)', created, updated, normalized_df.shape[0])
    return ImportReport(created=created, updated=updated, total_rows=normalized_df.shape[0])


def import_items(source_url: Optional[str] = None) -> ImportReport:
    raw_df = load_raw_dataframe(source_url)
    normalized_df = normalize_dataframe(raw_df)
    return upsert_items(normalized_df)


@cached(timeout=settings.AVG_PRICE_CACHE_TIMEOUT)
def get_avg_price_by_category():
    from decimal import Decimal, ROUND_HALF_UP
    qs = (
        Item.objects.values('category')
        .annotate(avg_price=Avg('price'))
        .order_by('category')
    )
    result = []
    for item in qs:
        avg_price = Decimal(str(item['avg_price'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        result.append({
            'category': item['category'],
            'avg_price': avg_price
        })
    return result

