import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.models import FinancialYearModel
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class BaseModelViewSet(ModelViewSet):
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    list_serializer_class = None
    fy_filtering_enabled = True

    serching_fields = [
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "created_by__full_name",
        "updated_by__full_name",
    ]
    ordering_fields = [
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]

    def get_serializer_class(self):
        if self.action in ("list", "archive_list") and self.list_serializer_class:
            return self.list_serializer_class

        return super().get_serializer_class()

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

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == "list":
            queryset = queryset.filter(deleted=False).order_by("-id")

        if self.fy_filtering_enabled:
            fy_id = self.request.query_params.get("fy_id")
            if fy_id:
                try:
                    fy = FinancialYearModel.objects.get(fid=fy_id)
                    queryset = queryset.filter(
                        created_at__date__gte=fy.start_date,
                        created_at__date__lte=fy.end_date,
                    )
                except FinancialYearModel.DoesNotExist:
                    return queryset.none()
            else:
                current_fy = FinancialYearModel.objects.filter(current=True).first()
                if current_fy and current_fy.start_date and current_fy.end_date:
                    queryset = queryset.filter(
                        created_at__date__gte=current_fy.start_date,
                        created_at__date__lte=current_fy.end_date,
                    )
        return queryset

    def get_instance_display(self, instance):
        return str(instance)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save(created_by=request.user)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name=self.queryset.model.__name__,
                description=f"Created {self.queryset.model.__name__} -  {self.get_instance_display(instance)}",
                request=request,
                payload=clean_payload(request.data),
            )

            return Response(
                {
                    "success": True,
                    "message": f"{self.queryset.model.__name__} Created Successfully",
                    "data" : instance.id
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        data = request.data.copy()
        data["updated_at"] = timezone.now()

        serializer = self.get_serializer(instance, data=data, partial=True)

        if serializer.is_valid():
            instance = serializer.save(updated_by=request.user)

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name=self.queryset.model.__name__,
                description=f"Updated {self.queryset.model.__name__} -  {self.get_instance_display(instance)}",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_202_ACCEPTED,
            )

        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.queryset.filter(pk=instance.pk).update(
                deleted=True,
                deleted_by=request.user,
                deleted_at=timezone.now(),
            )

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="ARCHIVE",
                module_name=self.queryset.model.__name__,
                description=f"Archived {self.queryset.model.__name__} -  {self.get_instance_display(instance)}",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "message": "Record Deleted Successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return custom_exception(e)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance.deleted:
                return Response(
                    {"success": False, "message": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = self.get_serializer(instance)

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return custom_exception(e)
