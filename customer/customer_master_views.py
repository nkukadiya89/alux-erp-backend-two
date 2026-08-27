import logging
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from customer.models import CustomerType
from customer.serializers import CustomerTypeListSerializer, CustomerTypeSerializer
from customer.permissions import CustomerTypePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from utils.export_excel import ExportUtility


logger = logging.getLogger(__name__)

class CustomerTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = CustomerType.objects.select_related(
        "created_by", "updated_by"
    ).all()
    serializer_class = CustomerTypeSerializer
    permission_classes = BaseModelViewSet.permission_classes + [CustomerTypePermission]
    search_fields = ["id", "name", "created_by__first_name", "created_by__last_name"]
    ordering_fields = ["name"]
    fy_filtering_enabled = False

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "name",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Name", "name"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]

        return ExportUtility.export_excel(
            queryset=queryset,
            columns=columns,
            filename="customer_type.xlsx",
            sheet_name="Customer Types",
        )

    @action(detail=False, methods=["GET"], url_path="export-pdf")
    def export_pdf(self, request):

        queryset = self.get_queryset()

        fields = [
            "name",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        ]

        headers = [
            "Customer Type",
            "Created At",
            "Created By",
            "Updated At",
            "Updated By",
        ]

        return ExportUtility.export_pdf(
            queryset=queryset,
            columns=list(zip(headers, fields)),
            filename="customer_type.pdf",
            title="Customer Type List",
        )