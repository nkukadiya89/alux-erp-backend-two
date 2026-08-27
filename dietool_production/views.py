from .models import (
    ActivityMaster,
    AnalysisMethod,
    CorrectionHistory, 
    DieFailureLog, 
    DieProductionLog, 
    DieMaintenanceLog,
    DieNitridingBatch,
    DieNitridingBatchDetail,
    ReasonForMaintenance,
    DieTrialLog, 
    MaintenanceType,
    CorrectionType,
    ReasonForCorrection,
    CorrectionInspectionType
)
from .serializers import (
    ActivityMasterSerializer,
    AnalysisMethodSerializer,
    CorrectionHistoryListSerializer,
    DieFailureLogListSerializer,
    DieFailureLogSerializer,
    DieProductionLogSerializer, 
    DieMaintenanceLogSerializer,
    DieNitridingBatchSerializer,
    DieNitridingBatchListSerializer,
    DieNitridingBatchDetailSerializer,
    DieTrialLogListSerializer, 
    DieTrialLogSerializer, 
    MaintenanceTypeSerializer, 
    DieMaintenanceLogListSerializer,
    CorrectionHistorySerializer,
    CorrectionTypeSerializer,
    ReasonForCorrectionSerializer,
    CorrectionInspectionTypeSerializer,
    ReasonForMaintenanceSerializer
)
from production.serializers import ProductionSerializer
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from production.models import Production
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.db.models import Q

class DieProductionLogViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DieProductionLog.objects.all()
    serializer_class = DieProductionLogSerializer

    @action(detail=False, methods=["get"], url_path="production-entry")
    def production_entry(self, request):
        queryset = (
            Production.objects
            .filter(
                deleted=False,
                die_tool__isnull=False,
            )
            .select_related(
                "planning",
                "press",
                "workorder",
                "customer",
                "die_profile",
                "die_tool",
                "alloy",
                "temper",
                "shift",
            )
            .prefetch_related(
                "operators",
                "supervisors",
                "billet_production",
                "idle_logs",
                "used_logs",
            )
            .order_by(
                "-production_date",
                "-id"
            )
        )

        # Die Tool wise filter
        die_tool_id = request.query_params.get("die_tool")
        if die_tool_id:
            queryset = queryset.filter(die_tool_id=die_tool_id)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = ProductionSerializer(
                page,
                many=True
            )

            return self.get_paginated_response({
                "success": True,
                "data": serializer.data,
            })

        serializer = ProductionSerializer(
            queryset,
            many=True
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

class DieMaintenanceLogViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DieMaintenanceLog.objects.all()
    serializer_class = DieMaintenanceLogSerializer
    list_serializer_class = DieMaintenanceLogListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        die_tool_id = self.request.query_params.get("die_tool")

        if die_tool_id:
            queryset = queryset.filter(die_tool_id=die_tool_id)

        return queryset

class DieNitridingBatchViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DieNitridingBatch.objects.all()
    serializer_class = DieNitridingBatchSerializer
    list_serializer_class = DieNitridingBatchListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                Q(batch_no__icontains=search)
                | Q(furnace__furnace_name__icontains=search)
                | Q(status__icontains=search)
            )

        return queryset

class DieNitridingBatchDetailViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DieNitridingBatchDetail.objects.all()
    serializer_class = DieNitridingBatchDetailSerializer

class DieTrialLogViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DieTrialLog.objects.all()
    serializer_class = DieTrialLogSerializer
    list_serializer_class = DieTrialLogListSerializer


class MaintananceTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = MaintenanceType.objects.all()
    serializer_class = MaintenanceTypeSerializer


class CorrectionTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = CorrectionType.objects.all()
    serializer_class = CorrectionTypeSerializer


class ReasonForCorrectionViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = ReasonForCorrection.objects.all()
    serializer_class = ReasonForCorrectionSerializer


class CorrectionInspectionTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = CorrectionInspectionType.objects.all()
    serializer_class = CorrectionInspectionTypeSerializer


class ActivityMasterViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = ActivityMaster.objects.all()
    serializer_class = ActivityMasterSerializer


class CorrectionHistoryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = CorrectionHistory.objects.all()
    serializer_class = CorrectionHistorySerializer
    list_serializer_class = CorrectionHistoryListSerializer


class AnalysisMethodViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = AnalysisMethod.objects.all()
    serializer_class = AnalysisMethodSerializer


class DieFailureLogViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DieFailureLog.objects.all()
    serializer_class = DieFailureLogSerializer
    list_serializer_class = DieFailureLogListSerializer

class ReasonForMaintenanceViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = ReasonForMaintenance.objects.all()
    serializer_class = ReasonForMaintenanceSerializer    