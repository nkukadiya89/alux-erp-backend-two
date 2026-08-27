# views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.pagination import Pagination

from .models import LogActivity
from .serializers import LogActivitySerializer


class LogActivityViewSet(ModelViewSet):
    queryset = LogActivity.objects.all().order_by("-timestamp")
    serializer_class = LogActivitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination

    http_method_names = ["get", "post", "put", "patch", "delete"]

    search_fields = [
        "action",
        "module_name",
        "ip_address",
        "discription",
        "action_by__username",
    ]
    ordering_fields = ["action", "timestamp", "module_name"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        try:
            fields_param = request.query_params.get("fields")
            if fields_param and fields_param.strip():
                requested_fields = [
                    f.strip() for f in fields_param.split(",") if f.strip()
                ]
                valid_fields = []

                for field in requested_fields:
                    try:
                        queryset.values(field)
                        valid_fields.append(field)
                    except Exception:
                        continue

                if valid_fields:
                    queryset = queryset.values(*valid_fields)
                    page = self.paginate_queryset(queryset)
                    if page is not None:
                        return self.get_paginated_response(
                            {"success": True, "data": list(page)}
                        )
                    return Response(
                        {"success": True, "data": list(queryset)},
                        status=status.HTTP_200_OK,
                    )

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return custom_exception(e)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["action_by"] = request.user.id

        # If frontend sends "ipAddress" instead of "ip_address", handle the key mapping
        if "ipAddress" in data:
            data["ip_address"] = data.pop("ipAddress")

        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            instance = serializer.save()
            return Response(
                {"success": True, "data": self.serializer_class(instance).data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        data["action_by"] = request.user.id
        serializer = self.serializer_class(instance, data=data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"success": True, "message": "Log activity deleted."},
            status=status.HTTP_200_OK,
        )
