from django.db.models import Prefetch

from common.master_views import BaseModelViewSet
from die.conversion_serializers import (
    ConversionRateItemsSerializer,
    ConversionRateSerializer,
    ConversionRateVersionsSerializer,
    ConversionRateListSerializer,
)
from die.models import ConversionRate, ConversionRateItems, ConversionRateVersions

class ConversionRateViewSet(BaseModelViewSet):
    queryset = (
        ConversionRate.objects.filter(deleted=False)
        .select_related("customer")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=ConversionRateItems.objects.filter(deleted=False).order_by("-id"),
            ),
            Prefetch(
                "items__versions",
                queryset=ConversionRateVersions.objects.filter(deleted=False).order_by("-id"),
            ),
        )
        .order_by("-created_at")
    )
    serializer_class = ConversionRateSerializer
    list_serializer_class = ConversionRateListSerializer
    search_fields = ["customer__customer_name"]
    ordering_fields = ["created_at", "updated_at"]


class ConversionRateItemsViewSet(BaseModelViewSet):
    queryset = (
        ConversionRateItems.objects.filter(deleted=False)
        .select_related(
            "conversion_rate", "die", "alloy", "temper", "created_by", "updated_by"
        )
        .prefetch_related("versions")
        .order_by("-created_at")
    )
    serializer_class = ConversionRateItemsSerializer
    search_fields = ["die__die_number", "alloy__alloy_code", "temper__name"]
    ordering_fields = ["created_at", "updated_at"]


class ConversionRateVersionsViewSet(BaseModelViewSet):
    queryset = (
        ConversionRateVersions.objects.filter(deleted=False)
        .select_related("conversion_rate_items", "created_by", "updated_by")
        .order_by("-created_at")
    )
    serializer_class = ConversionRateVersionsSerializer
    search_fields = ["adjustment_type", "conversion"]
    ordering_fields = ["date", "effective_from", "effective_to", "created_at"]
