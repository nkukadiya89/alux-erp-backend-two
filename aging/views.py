from rest_framework import status
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from aging.models import AgeingBatch, AgeingBatchDetail, AgeingTemperatureLog
from aging.serializers import (
    AgeingBatchDetailSerializer,
    AgeingBatchSerializer,
    AgeingListSerializer,
    AgeingTemperatureLogSerializer,
)
from common.master_views import BaseModelViewSet
from utils.error_handling import custom_exception
from common.models import ArchiveMixin


class AgeingBatchViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        AgeingBatch.objects.all()
        .prefetch_related("batch_details", "temperature_logs")
    )
    serializer_class = AgeingBatchSerializer
    list_serializer_class = AgeingListSerializer

    search_fields = ["batch_no", "heat_treatment_no", "furnace_no", "status"]

    ordering_fields = ["id", "batch_no", "ageing_date", "shift", "status", "created_at"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["created_at"] = timezone.now()
        data["updated_at"] = None

        serializer = self.get_serializer(data=data)

        try:
            if serializer.is_valid(raise_exception=True):
                ageing_batch = serializer.save(created_by=request.user)

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data.copy()
        data["updated_at"] = timezone.now()

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True)

            if serializer.is_valid(raise_exception=True):
                ageing_batch = serializer.save(updated_by=request.user)

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.deleted = True
            instance.deleted_at = timezone.now()
            instance.deleted_by = request.user
            instance.save()

            return Response(
                {"success": True, "message": "Ageing batch deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)


class AgeingBatchDetailViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = AgeingBatchDetail.objects.all()
    serializer_class = AgeingBatchDetailSerializer


class AgeingTemperatureLogViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = AgeingTemperatureLog.objects.all()
    serializer_class = AgeingTemperatureLogSerializer
