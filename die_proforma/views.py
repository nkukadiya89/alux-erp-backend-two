from common.master_views import BaseModelViewSet
from die_proforma.models import DieProforma
from die_proforma.serializers import DieProformaSerializer
from common.models import ArchiveMixin

class DieProformaViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        DieProforma.objects.select_related(
            "customer", "created_by", "updated_by", "deleted_by"
        )
        .prefetch_related("die_proforma_details_proforma")
        .order_by("-id")
    )
    serializer_class = DieProformaSerializer

    ordering_fields = [
        "proforma_date",
        "proforma_no",
    ]
