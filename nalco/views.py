from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from nalco.models import NalcoMaster
from nalco.serializers import NalcoMasterSerializers
from utils.export_excel import ExportUtility


class NalcoMasterViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = NalcoMaster.objects.filter(deleted=False).order_by("-date")
    serializer_class = NalcoMasterSerializers
    fy_filtering_enabled = False

    search_fields = [
        "id",
        "date",
        "ignot_grade",
        "rate_per_mt",
        "created_at",
        "created_by__first_name",
        "created_by__last_name",
        "updated_at",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = [
        "date",
        "ignot_grade",
        "rate_per_mt",
        "created_at",
        "updated_at",
    ]
    

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "date",
            "ignot_grade",
            "rate_per_kg",
            "adjustment_type",
            "adjustment_value",
            "final_rate_mt",
            "diff_kg",
            "diff_mt",
            "percentage_change",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Date", "date"),
            ("Ignot_grade", "ignot_grade"),
            ("Rate_per_kg", "rate_per_kg"),
            ("Adjustment_type", "adjustment_type"),
            ("Adjustment_value", "adjustment_value"),
            ("Final_rate_mt", "final_rate_mt"),
            ("Diff_kg", "diff_kg"),
            ("Diff_mt", "diff_mt"),
            ("Percentage_change", "percentage_change"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]
        export = ExportUtility()

        return  export.export_excel(
            queryset=queryset,
            columns=columns,
            filename="nalco.xlsx",
            sheet_name="nalco",
        )    

    @action(methods=["get"], detail=False, url_path="latest-nalco-rate")
    def latest_nalco_rate(self, request, *args, **kwargs):
        try:
            latest_nalco = (
                NalcoMaster.objects.filter(deleted=False).order_by("-date").first()
            )

            if latest_nalco:
                serializer = self.get_serializer(latest_nalco)
                return Response({"success": True, "data": serializer.data})

            return Response(
                {"success": False, "message": "No nalco rates found."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(methods=["get"], detail=False, url_path="latest-by-grade")
    def latest_by_grade(self, request):
        try:
            grade = request.query_params.get("grade")

            if not grade:
                return Response(
                    {"success": False, "message": "grade is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            latest = (
                NalcoMaster.objects.filter(
                    ignot_grade=grade,
                    deleted=False,
                )
                .order_by("-date")
                .first()
            )

            if latest:
                return Response(
                    {"success": True, "data": self.get_serializer(latest).data}
                )

            return Response(
                {"success": False, "message": "No data found for this grade"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
