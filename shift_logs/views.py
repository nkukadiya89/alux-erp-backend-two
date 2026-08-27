from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.master_views import BaseModelViewSet
from utils.error_handling import custom_exception
from utils.pagination import Pagination
from .models import ShiftLog
from .serializers import (
    ShiftLogListSerializer,
    ShiftLogSerializer,
)


class ShiftLogViewSet(BaseModelViewSet):

    queryset = ShiftLog.objects.all().order_by("-date")
    serializer_class = ShiftLogSerializer
    list_serializer_class = ShiftLogListSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    # List filtering is driven by start_date/end_date on business `date`.
    # created_at FY filtering would hide valid historical shift logs.
    fy_filtering_enabled = False

    def get_queryset(self):
        queryset = super().get_queryset()

        #start_date = self.request.query_params.get("start_date")
        #end_date = self.request.query_params.get("end_date")
        shift = self.request.query_params.get("shift")
        press = self.request.query_params.get("press")

        if shift:
            queryset = queryset.filter(shift=shift)

        if press:
            queryset = queryset.filter(press=press)


        return queryset

    def create(self, request, *args, **kwargs):

        data = request.data.copy()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        serializer.save(created_by=request.user)

        return Response(
            {
                "status": True,
                "message": "Shift Log created successfully",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):

        instance = self.get_object()

        if instance.status == "Submitted":
            return Response(
                {"status": False, "message": "Submitted shift cannot be edited"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(updated_by=request.user)

        return Response(
            {
                "status": True,
                "message": "Shift Log updated successfully",
                "data": serializer.data,
            }
        )