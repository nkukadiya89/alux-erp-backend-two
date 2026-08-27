from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from utils.error_handling import custom_exception

from .models import Vendor
from .serializers import VendorListSerializer, VendorSerializer


class VendorViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Vendor.objects.all()
        .select_related("created_by")
        .prefetch_related("vendor_key_person", "vendor_bank_details")
    )
    serializer_class = VendorSerializer
    list_serializer_class = VendorListSerializer

    search_fields = [
        "id",
        "business_type",
        "import_export_code",
        "beneficiary_agent_code",
        "pan_number",
        "code",
        "fax_number",
        "website",
        "person_name",
        "designation",
        "email",
        "phone",
        "udyam_aadhaar_no",
        "udyam_aadhaar_no_verified",
        "vendor_registered_name",
        "vendor_trade_name",
        "gst_no",
        "gst_no_verified",
        "vendor_code_as_per_company_erp",
        "is_active",
        "status",
        "vendor_trade_name",
        "registered_business_address_building",
        "registered_business_address_area",
        "registered_business_address_landmark",
        "registered_business_address_pincode",
        "registered_business_address_state",
        "registered_business_address_city",
        "registered_business_address_country",
        "trading_address_building",
        "trading_address_area",
        "trading_address_landmark",
        "trading_address_pincode",
        "trading_address_state",
        "trading_address_city",
        "trading_address_country",
        "vendor_logo",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = [
        "id",
        "import_export_code",
        "beneficiary_agent_code",
        "pan_number",
        "code",
        "fax_number",
        "website",
        "person_name",
        "designation",
        "phone",
        "udyam_aadhaar_no",
        "udyam_aadhaar_no_verified",
        "vendor_registered_name",
        "vendor_trade_name",
        "gst_no",
        "gst_no_verified",
        "vendor_code_as_per_company_erp",
        "vendor_trade_name",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            serializer = VendorListSerializer(
                page if page is not None else queryset, many=True
            )
            data = serializer.data

            fields_param = request.query_params.get("fields")
            requested_fields = []
            if fields_param:
                requested_fields = list(
                    filter(
                        None, map(str.strip, fields_param.replace(" ", "").split(","))
                    )
                )

            def extract_nested_field(obj, field_path):
                try:
                    for part in field_path.split("__"):
                        if isinstance(obj, list):
                            obj = [
                                o.get(part, None) if isinstance(o, dict) else None
                                for o in obj
                            ]
                        else:
                            obj = obj.get(part, None)
                        if obj is None:
                            return None
                    return obj
                except Exception:
                    return None

            def filter_fields(data, fields):
                if not fields:
                    return data
                if isinstance(data, list):
                    return [
                        {field: extract_nested_field(item, field) for field in fields}
                        for item in data
                    ]
                elif isinstance(data, dict):
                    return {
                        field: extract_nested_field(data, field) for field in fields
                    }
                return data

            serializer = self.get_serializer(
                page if page is not None else queryset, many=True
            )
            data = serializer.data

            filtered_data = filter_fields(data, requested_fields)

            response_data = {
                "success": True,
                "data": filtered_data,
            }

            if page is not None:
                paginated_response = self.get_paginated_response(response_data)
                return paginated_response

            return Response(response_data)

        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_at"] = timezone.now()
        data["updated_at"] = None
        data["approved_at"] = None

        serializer = self.serializer_class(data=data, context={"request": request})

        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        data["updated_at"] = timezone.now()
        data["approved_at"] = None

        try:
            serializer = self.serializer_class(
                instance, data=data, partial=True, context={"request": request}
            )

            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return custom_exception(e)
