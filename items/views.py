from django_filters import rest_framework as filters
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Item
from .serializers import AveragePriceSerializer, ItemSerializer
from .services import get_avg_price_by_category


class ItemFilter(filters.FilterSet):
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Item
        fields = ['category']


class ItemListView(generics.ListAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    filterset_class = ItemFilter
    ordering_fields = ['price', 'updated_at', 'name']


class AveragePriceByCategoryView(APIView):
    serializer_class = AveragePriceSerializer

    def get(self, request, *args, **kwargs):
        data = get_avg_price_by_category()
        serializer = self.serializer_class(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
