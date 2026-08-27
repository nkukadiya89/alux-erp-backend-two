import logging

from django.db import transaction
from django.db.models import Prefetch
from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from utils.error_handling import custom_exception
from utils.pagination import Pagination

from .models import DieRequisition, DieRequisitionDetail
from .serializers import (
    DieRequisitionDetailCloseSerializer,
    DieRequisitionDetailCreateSerializer,
    DieRequisitionDetailSerializer,
    DieRequisitionListSerializer,
    DieRequisitionRejectSerializer,
    DieRequisitionSerializer,
    DieRequisitionWriteSerializer,
)

logger = logging.getLogger("file")


class DieRequisitionViewSet(BaseModelViewSet):
    search_fields = ["requisition_no", "remarks", "customer__customer_name"]
    ordering_fields = [
        "requisition_date",
        "required_date",
        "created_at",
        "requisition_no",
    ]

    def get_queryset(self):
        queryset = (
            DieRequisition.objects.filter(deleted=False)
            .select_related("workorder_no", "customer", "created_by", "updated_by")
            .prefetch_related(
                Prefetch(
                    "die_requisition",
                    queryset=DieRequisitionDetail.objects.filter(
                        deleted=False
                    ).select_related("die_tool", "press"),
                )
            )
            .order_by("-id")
        )
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return DieRequisitionListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return DieRequisitionWriteSerializer
        return DieRequisitionSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["created_at"] = timezone.now()
        data["created_by"] = request.user
        data["updated_at"] = None
        serializer = self.get_serializer(data=data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save(created_by=request.user)
            logger.info("Die Requisition created successfully.")
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data.copy()
        try:
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user, updated_at=timezone.now())
            logger.info("Die Requisition updated successfully.")
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return custom_exception(e)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def _generate_requisition_no(self):
        from utils.generate_number import generate_die_requisition_no

        return generate_die_requisition_no()

    @action(detail=True, methods=["post"], url_path="reject-requisition")
    def reject_requisition(self, request, pk=None):
        requisition = get_object_or_404(DieRequisition, pk=pk, deleted=False)

        if requisition.status == "Rejected":
            return Response(
                {"detail": "Requisition already rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DieRequisitionRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            requisition.status = "Rejected"
            requisition.rejection_reason = serializer.validated_data["rejection_reason"]
            requisition.save()

        return Response(
            {"detail": "Die Requisition rejected successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="close-requisition")
    def close_requisition(self, request, pk=None):
        requisition = get_object_or_404(DieRequisition, pk=pk, deleted=False)

        if requisition.status == "Closed":
            return Response(
                {"detail": "Requisition already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DieRequisitionDetailCloseSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            for item in serializer.validated_data:
                detail = get_object_or_404(
                    DieRequisitionDetail,
                    pk=item["id"],
                    requisition=requisition,
                    deleted=False,
                )

                detail.actual_qty_produced = item["actual_qty_produced"]
                detail.billets_used = item["billets_used"]
                detail.die_return_date = item["die_return_date"]
                detail.die_condition_after = item["die_condition_after"]
                detail.remarks = item.get("remarks")
                detail.save()

            requisition.status = "Closed"
            requisition.save()

        return Response(
            {"detail": "Die Requisition closed successfully."},
            status=status.HTTP_200_OK,
        )


class DieRequisitionDetailViewSet(viewsets.ModelViewSet):
    queryset = DieRequisitionDetail.objects.filter(deleted=False)
    serializer_class = DieRequisitionDetailSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    ordering_fields = ["created_at", "life_balance", "expected_output_kg"]
    ordering = ["id"]

    def get_queryset(self):
        queryset = DieRequisitionDetail.objects.filter(deleted=False).select_related(
            "requisition", "die_tool", "press", "created_by", "updated_by"
        )

        requisition_id = self.request.query_params.get("requisition_id")
        if requisition_id:
            queryset = queryset.filter(requisition_id=requisition_id)

        return queryset

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update", "bulk_upsert"]:
            return DieRequisitionDetailCreateSerializer
        return DieRequisitionDetailSerializer

    @action(detail=False, methods=["patch"], url_path="bulk-upsert")
    @transaction.atomic
    def bulk_upsert(self, request):
        requisition_id = request.query_params.get("requisition_id")
        if not requisition_id:
            raise ValidationError({"requisition_id": "This query param is required."})

        requisition = get_object_or_404(DieRequisition, id=requisition_id)

        payload = request.data
        if not isinstance(payload, list):
            raise ValidationError("Expected a list of detail objects.")

        existing_details = {
            d.id: d
            for d in DieRequisitionDetail.objects.filter(
                requisition=requisition, deleted=False
            )
        }

        response_instances = []

        for item in payload:
            detail_id = item.get("id")
            if detail_id:
                if detail_id not in existing_details:
                    raise ValidationError(
                        f"Detail id {detail_id} does not belong to requisition {requisition_id}"
                    )

                detail = existing_details[detail_id]
                serializer = self.get_serializer(detail, data=item, partial=True)
                serializer.is_valid(raise_exception=True)
                instance = serializer.save(
                    updated_by=request.user,
                )

            else:
                serializer = self.get_serializer(data=item)
                serializer.is_valid(raise_exception=True)
                instance = serializer.save(
                    requisition=requisition,
                    created_by=request.user,
                )

            response_instances.append(instance)

        requisition.status = "Issued"
        requisition.updated_by = request.user
        requisition.updated_at = timezone.now()
        requisition.save(update_fields=["status", "updated_by", "updated_at"])

        read_serializer = DieRequisitionDetailCreateSerializer(
            response_instances, many=True
        )

        return Response(
            {
                "success": True,
                "message": "Die Requisition Details upserted successfully",
                "data": read_serializer.data,
            },
            status=status.HTTP_200_OK,
        )
