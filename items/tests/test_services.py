from decimal import Decimal

import pandas as pd
import pytest
from django.utils import timezone

from items.models import Item
from items.services import (
    get_avg_price_by_category,
    normalize_dataframe,
    upsert_items,
)


def test_normalize_dataframe_maps_aliases_and_cleans_values():
    raw_df = pd.DataFrame(
        [
            {
                'Product_Name': ' Widget ',
                'Category_Name': ' Tools ',
                'Amount': '19.999',
                'Last_Updated': '2024-01-01T08:00:00Z',
                'sku': 'W-1',
            },
        ]
    )

    normalized = normalize_dataframe(raw_df)

    assert list(normalized.columns) == ['source_uid', 'name', 'category', 'price', 'updated_at']
    row = normalized.iloc[0]
    assert row['name'] == 'Widget'
    assert row['category'] == 'Tools'
    assert row['price'] == Decimal('20.00')
    assert str(row['source_uid']).startswith('a0') or len(row['source_uid']) == 40
    assert row['updated_at'].tzinfo is not None


@pytest.mark.django_db
def test_upsert_items_updates_existing_records():
    base_df = pd.DataFrame(
        [
            {
                'source_uid': 'abc',
                'name': 'Widget',
                'category': 'Tools',
                'price': Decimal('10.00'),
                'updated_at': pd.Timestamp('2024-01-01T08:00:00Z'),
            }
        ]
    )
    upsert_items(base_df)
    assert Item.objects.count() == 1

    updated_df = pd.DataFrame(
        [
            {
                'source_uid': 'abc',
                'name': 'Widget',
                'category': 'Tools',
                'price': Decimal('12.00'),
                'updated_at': pd.Timestamp('2024-02-01T08:00:00Z'),
            }
        ]
    )
    upsert_items(updated_df)

    item = Item.objects.get(source_uid='abc')
    assert item.price == Decimal('12.00')
    assert timezone.is_aware(item.updated_at)


@pytest.mark.django_db
def test_get_avg_price_by_category(settings, django_assert_num_queries):
    settings.CACHEOPS_ENABLED = False
    Item.objects.create(
        source_uid='1',
        name='Widget',
        category='Tools',
        price=Decimal('10.00'),
        updated_at=timezone.now(),
    )
    Item.objects.create(
        source_uid='2',
        name='Gadget',
        category='Tools',
        price=Decimal('20.00'),
        updated_at=timezone.now(),
    )

    with django_assert_num_queries(1):
        data = get_avg_price_by_category()

    assert len(data) == 1
    assert data[0]['category'] == 'Tools'
    assert Decimal(data[0]['avg_price']) == Decimal('15')

