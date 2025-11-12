from rest_framework import serializers

from .models import Item


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'name', 'category', 'price', 'updated_at']


class AveragePriceSerializer(serializers.Serializer):
    category = serializers.CharField()
    avg_price = serializers.DecimalField(max_digits=12, decimal_places=2)

