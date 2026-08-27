from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from transporter.permissions import TransporterPermission
from .models import Transporter
from .serializer import TransporterSerializer, TransporterDropdownSerializer
from utils.export_excel import ExportUtility
from transporter.filters import TransporterFilter


class TransporterViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = Transporter.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransporterFilter

    def get_queryset(self):
        if self.action in ["archive_list", "unarchive"]:
            queryset = Transporter.objects.all().order_by("-id")
        else:
            queryset = Transporter.objects.filter(deleted=False).order_by("-id")

        is_active = self.request.query_params.get("is_active")

        if is_active and self.action not in ["archive_list", "unarchive"]:
            queryset = queryset.filter(is_active=is_active)
        return queryset

    serializer_class = TransporterSerializer
    permission_classes = [TransporterPermission]

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown for Transporter (id, party_name, party_code)."""
        queryset = self.get_queryset().only("id", "party_name", "party_code")
        serializer = TransporterDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


    @action(detail=False, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request):
        queryset = self.get_queryset().filter(deleted=False)

        fields = [
            "party_name",
            "party_code",
            "opening_balance",
            "balance_type",
            "is_cash_amount",
            "address",
            "city",
            "pincode",
            "mobile_no",
            "phone_no",
            "email_id",
            "send_sms_type",
            "is_active",
        ]

        headers = [
            "Party Name",
            "Party Code",
            "Opening Balance",
            "Balance Type",
            "Cash?",
            "Address",
            "City",
            "Pincode",
            "Mobile",
            "Phone",
            "Email",
            "SMS Type",
            "Status",
        ]

        return ExportUtility.export_to_pdf(
            queryset,
            fields,
            headers,
            file_name="transporters.pdf",
            title="Transporter List",
            col_widths=[60, 60, 70, 40, 40, 60, 60, 60, 60, 60, 90, 50, 40],
        )
