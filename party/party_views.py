import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from party.models import Party
from party.serializers import PartySerializers
from utils.error_handling import custom_exception
from utils.log_activity import log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class PartyViewSet(ModelViewSet):
    queryset = (
        Party.objects.filter(deleted=False)
        .select_related("created_by", "updated_by", "deleted_by")
        .order_by("-id")
    )
    serializer_class = PartySerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "name",
        "sundry_group",
        "account_group",
        "customer_category",
        "customer_subcategory",
        "customer_type",
        "office_address",
        "registered_address",
        "shipping_address",
        "applicable_gst",
        "party_section_no",
        "bank_name",
        "bank_branch_name",
        "bank_branch_address",
        "bank_account_number",
        "bank_ifsc_code",
        "gst_no",
        "gst_type",
        "pan_number",
        "udhyam_no",
        "sgst_number",
        "cgst_number",
        "unique_id",
        "deleted",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = [
        "name",
        "sundry_group",
        "account_group",
        "customer_category",
        "customer_subcategory",
        "customer_type",
        "office_address",
        "registered_address",
        "shipping_address",
        "applicable_gst",
        "party_section_no",
        "bank_name",
        "bank_branch_name",
        "bank_branch_address",
        "bank_account_number",
        "bank_ifsc_code",
        "gst_no",
        "gst_type",
        "pan_number",
        "udhyam_no",
        "sgst_number",
        "cgst_number",
        "unique_id",
        "deleted",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(deleted=False)
        page = self.paginate_queryset(queryset)
        try:
            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )
            serializer = self.serializer_class(queryset, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        except Exception as e:
            return custom_exception(e)

    def get_queryset(self):
        queryset = super().get_queryset()
        id: str = self.request.query_params.get("id")  # type: ignore
        name: str = self.request.query_params.get("name")  # type: ignore
        if id is not None:
            queryset = queryset.filter(id=id)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_by"] = request.user.id
        data["created_at"] = timezone.now()
        data["updated_at"] = None

        serializer = self.serializer_class(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                logger.info("Record created successfully.")
                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                logger.error(f"Error in creating record : {serializer.errors}")
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return custom_exception(e)

    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_by"] = request.user.id
        data["updated_at"] = timezone.now()

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info("Record updated successfully.")
                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                logger.error(f"Error in updating record : {serializer.errors}")
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.deleted = True
            instance.save()
            return Response(
                {"success": True, "message": "Party Deleted"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Exception as e:
            return custom_exception(e)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({"success": True, "data": serializer.data})
        except Exception as e:
            return Response(
                {"success": False, "message": f"No Die matches the given ID."},
                status=status.HTTP_204_NO_CONTENT,
            )

    @action(methods=["get"], detail=False, url_path="archive-list")
    def archive_list(self, request, *args, **kwargs):
        try:
            queryset = Party.objects.filter(deleted=True).order_by("-deleted_at")
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(
                page if page is not None else queryset, many=True
            )

            response_data = {"success": True, "data": serializer.data}
            if page is not None:
                return self.get_paginated_response(response_data)
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(methods=["post"], detail=True, url_path="unarchive")
    def unarchive(self, request, pk=None):
        try:
            instance = Party.objects.get(pk=pk, deleted=True)
        except Party.DoesNotExist:
            return Response(
                {"success": False, "message": "Archived party record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        instance.deleted = False
        instance.deleted_by = None
        instance.deleted_at = None
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        log_user_activity(
            user=request.user,
            action="RESTORE",
            module_name="Party",
            description=f"Unarchived party record (ID: {instance.id})",
            request=request,
            payload=None,
        )

        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Party record unarchived successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
