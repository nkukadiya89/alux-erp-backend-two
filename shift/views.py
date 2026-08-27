from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination
from shift.permissions import ShiftMasterPermission
from .models import ShiftMaster
from .serializers import ShiftMasterSerializer
from rest_framework.permissions import IsAuthenticated


class ShiftMasterViewSet(viewsets.ModelViewSet):
    queryset = ShiftMaster.objects.all().order_by("id")
    serializer_class = ShiftMasterSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated, ShiftMasterPermission]
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ["shift_name", "start_time", "end_time", "duration_minutes"]

    ordering_fields = [
        "id",
        "shift_name",
        "start_time",
        "end_time",
        "duration_minutes",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")

        shift = request.query_params.get("shift_name")
        if shift:
            queryset = queryset.filter(shift_name__icontains=shift)

        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        payload = clean_payload(request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)

        log_user_activity(
            user=request.user,
            action="CREATE",
            module_name="Shift Master",
            description=f"Created Shift Master (ID: {serializer.instance.id})",
            request=request,
            payload=payload,
        )

        return Response(
            {
                "success": True,
                "message": "Shift Master created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Shift Master",
                description=f"Updated Shift Master (ID: {instance.id})",
                request=request,
                payload=payload,
            )

            return Response(
                {
                    "success": True,
                    "message": "Shift Master updated successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": f"Error updating: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance_id = instance.id
            instance_name = instance.shift_name

            instance.delete()

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="Shift Master",
                description=f"Shift Master (ID: {instance_id}, Name: {instance_name}) deleted permanently.",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "message": "Shift Master deleted successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error during delete: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
