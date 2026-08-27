import logging
from common.master_serializers import UOMSerializers, YieldUnitSerializers
from common.master_views import BaseModelViewSet
from common.models import UOM, ArchiveMixin, GstType, JobWorkType, PackingMode, SectionType, StoreType, YieldUnit
from common.serializers import GstTypeSerializer, JobWorkSerializer, PackingModeSerializers, SectionTypeSerializer, StoreTypeSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from common.models import FinancialYearModel
from common.serializers import FinancialYearSerializer
from utils.financial_year_data import set_default_financial_year
from common.permissions import PackingModePermission
from rest_framework.permissions import IsAuthenticated
from django.db import utils
from utils.pagination import Pagination
from utils.error_handling import custom_exception
from utils.export_excel import ExportUtility

from rest_framework import viewsets
logger = logging.getLogger("file")


class PackingModeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = PackingMode.objects.all()
    serializer_class = PackingModeSerializers
    permission_classes = [IsAuthenticated, PackingModePermission]

    search_fields = BaseModelViewSet.serching_fields + ["name", "code", "description"]
    ordering_fields = ["name", "code"]

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "code",
            "name",
            "description",
            "price_per_kg",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Code", "code"),
            ("Name", "name"),
            ("Description", "description"),
            ("Price Per Kg", "price_per_kg"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]

        return ExportUtility.export_excel(
            queryset=queryset,
            columns=columns,
            filename="packing_mode.xlsx",
            sheet_name="Packing Modes",
        )    


class UOMViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = UOM.objects.all()
    serializer_class = UOMSerializers
    fy_filtering_enabled = False

    search_fields = BaseModelViewSet.serching_fields + ["uom_code", "uom_name", "uom_type"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["uom_code", "uom_name", "uom_type"]


class YieldUnitViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = YieldUnit.objects.all().order_by("-id")
    serializer_class = YieldUnitSerializers
    fy_filtering_enabled = False

    search_fields = BaseModelViewSet.serching_fields + ["id", "name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["id", "name"]


class StoreTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = StoreType.objects.all().order_by("-id")
    serializer_class = StoreTypeSerializer

    search_fields = BaseModelViewSet.serching_fields + ["id", "name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["id", "name"]


class SectionTypeViewSet(BaseModelViewSet):
    queryset = (
        SectionType.objects.all()
        .select_related("created_by", "updated_by")
        .order_by("name")
    )
    serializer_class = SectionTypeSerializer
    fy_filtering_enabled = False
    
    search_fields = BaseModelViewSet.serching_fields + ["name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["name"]


class JobWorkTypeViewSet(viewsets.ModelViewSet):
    queryset = JobWorkType.objects.all().order_by("id")
    serializer_class = JobWorkSerializer
    pagination_class = Pagination

    search_fields = BaseModelViewSet.serching_fields + ["name", "discription"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["name", "discription"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        try:
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.get_serializer(queryset, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        except Exception as e:
            return custom_exception(e)


class GstTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = GstType.objects.all().order_by("-id")
    serializer_class = GstTypeSerializer

    search_fields = ["name", "full_name"]
    ordering_fields = ["name", "full_name", "percentage"]


class FinancialYearViewSet(BaseModelViewSet, ArchiveMixin):
    serializer_class = FinancialYearSerializer

    search_fields = ["financial_year", "start_date", "end_date"]
    ordering_fields = ["financial_year", "start_date", "end_date"]

    def get_queryset(self):
        return FinancialYearModel.objects.filter(deleted=False).order_by("-fid")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["post"], url_path="set-current")
    def set_current_year(self, request):
        fid = request.data.get("fid")
        if not fid:
            return Response({"success": False, "message": "fid is required."}, status=400)

        try:
            FinancialYearModel.objects.all().update(current=False)
            obj = FinancialYearModel.objects.get(fid=fid)
            obj.current = True
            obj.save()

            return Response({
                "success": True,
                "message": f"{obj.financial_year} is set as current year.",
            })
        except FinancialYearModel.DoesNotExist:
            return Response({"success": False, "message": "Financial year not found."}, status=404)
