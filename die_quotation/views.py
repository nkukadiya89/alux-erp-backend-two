from django_filters.rest_framework import DjangoFilterBackend
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from die_quotation.models import DieQuotation
from die_quotation.serializers import (
    DieQuotationListSerializer,
    DieQuotationSerializers,
)
from die_quotation.filters import DieQuotationFilter


class DieQuotationViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DieQuotation.objects.all().select_related("customer").order_by("-id")
    serializer_class = DieQuotationSerializers
    list_serializer_class = DieQuotationListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DieQuotationFilter
