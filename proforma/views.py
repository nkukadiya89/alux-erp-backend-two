from django_filters.rest_framework import DjangoFilterBackend
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from proforma.filters import ProformaFilter
from proforma.models import Proforma
from proforma.serializers import ProformaSerializers
from proforma.sort_serializers import ProformaListSerializers


class ProformaViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Proforma.objects.select_related(
            "workorder", "customer", "created_by", "updated_by", "deleted_by"
        )
        .prefetch_related("proforma_details_proforma", "packing_mode")
        .order_by("-id")
    )
    serializer_class = ProformaSerializers
    list_serializer_class = ProformaListSerializers
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProformaFilter

    ordering_fields = [
        "proforma_date",
        "freight_charges",
        "proforma_no",
    ]
