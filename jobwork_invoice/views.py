from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from jobwork_invoice.filters import JobworkInvoiceFilter
from jobwork_invoice.models import JobworkInvoice, JobworkInvoiceLine
from jobwork_invoice.serializers import (
    JobworkInvoiceLineSerializer,
    JobworkInvoiceSerializer,
)


class JobworkInvoiceViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = (
        JobworkInvoice.objects.select_related(
            "vendor",
            "jobwork_type",
            "plant",
            "created_by",
            "updated_by",
            "shift",
        )
        .prefetch_related(
            Prefetch(
                "invoice_lines",
                queryset=JobworkInvoiceLine.objects.filter(deleted=False).select_related(
                    "production",
                    "workorder",
                    "workorder_detail",
                    "section_no",
                    "die_no",
                    "alloy",
                    "temper",
                ),
            )
        )
        .order_by("-created_at")
    )
    serializer_class = JobworkInvoiceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = JobworkInvoiceFilter
    ordering_fields = ["id", "challan_date", "challan_no"]

    def get_instance_display(self, instance):
        return instance.challan_no


class JobworkInvoiceLineViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = JobworkInvoiceLine.objects.filter(deleted=False).order_by("-created_at")
    serializer_class = JobworkInvoiceLineSerializer
