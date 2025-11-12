from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from items.models import Item


@pytest.mark.django_db
def test_items_endpoint_filters_by_price_range(client, settings):
    settings.CACHEOPS_ENABLED = False
    Item.objects.create(
        source_uid='item-1',
        name='Budget Mouse',
        category='Electronics',
        price=Decimal('15.00'),
        updated_at=timezone.now(),
    )
    Item.objects.create(
        source_uid='item-2',
        name='Premium Mouse',
        category='Electronics',
        price=Decimal('55.00'),
        updated_at=timezone.now(),
    )

    url = reverse('item-list')
    response = client.get(url, {'price_min': 10, 'price_max': 20})

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 1
    assert payload['results'][0]['name'] == 'Budget Mouse'

