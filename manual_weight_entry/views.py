import json
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from utils.log_activity import clean_payload, log_user_activity
from .models import ManualWeightEntry
from .serializer import ManualWeightEntrySerializer

User = get_user_model()


class ManualWeightEntryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = ManualWeightEntry.objects.all()
    serializer_class = ManualWeightEntrySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "vehicle_no",
                "party_name",
                "vehicle_type",
                "material",
                "purchaser",
                "seller",
                "created_by",
                "updated_by",
                "deleted_by",
            )
            .order_by("-id")
        )

    search_fields = BaseModelViewSet.serching_fields + [
        "id",
        "gross_weight",
        "tare_weight",
        "net_weight",
        "date_time_first",
        "date_time_second",
        "mound",
        "serial_no",
        "total_copy",
        "cash_party_name",
        "party_mobile_no",
        "party_mobile_no",
        "party_name__party_name",
        "vehicle_type__vehicle_type",
        "material__item_name",
    ]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "id",
        "gross_weight",
        "tare_weight",
        "net_weight",
        "date_time_first",
        "date_time_second",
        "mound",
        "serial_no",
        "total_copy",
        "vehicle_no",
        "cash_party_name",
        "party_mobile_no",
        "party_name",
        "vehicle_no",
        "vehicle_type",
        "material",
        "material",
        "purchaser",
        "seller",
        "party_name_display",
        "vehicle_type_name",
        "purchaser_name",
    ]
    UPLOAD_FIELDS = ["capture_photo_manual_1", "capture_photo_manual_2"]

    def create(self, request, *args, **kwargs):
        data = {}
        if "data" in request.POST:
            try:
                data = json.loads(request.POST.get("data", "{}"))
            except Exception:
                return Response(
                    {"success": False, "message": "Invalid JSON in 'data'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        files_to_upload = {}
        for field in self.UPLOAD_FIELDS:
            if field in request.FILES:
                files_to_upload[field] = request.FILES[field]
            data.pop(field, None)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user)

        if files_to_upload:
            instance.upload_doc(doc_dict=files_to_upload)
            instance.refresh_from_db()
            response_serializer = self.get_serializer(instance)
            response_data = response_serializer.data
        else:
            response_data = serializer.data

        log_user_activity(
            user=request.user,
            action="CREATE",
            module_name="ManualWeightEntry",
            description=f"Created Manual Weight Entry for vehicle: {instance.vehicle_no}",
            request=request,
            payload=clean_payload(response_data),
        )

        return Response(
            {
                "success": True,
                "message": "Created successfully",
                "data": response_data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_data = self.get_serializer(instance).data

        data = request.data.copy()

        if "data" in request.data:
            try:
                json_data = json.loads(request.data["data"])
                data.update(json_data)
            except:
                pass

        files_to_upload = {}
        for field in self.UPLOAD_FIELDS:
            if field in request.FILES:
                files_to_upload[field] = request.FILES[field]
            data.pop(field, None)
        clear_fields = []
        for field in self.UPLOAD_FIELDS:
            if field in request.data and request.data.get(field) in (None, "null", ""):
                clear_fields.append(field)

        if not data and not files_to_upload and not clear_fields:
            return Response(
                {"success": False, "message": "No data provided"}, status=400
            )

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(updated_by=request.user)

        if clear_fields:
            for field in clear_fields:
                setattr(instance, field, None)
            instance.save(update_fields=clear_fields)

        if files_to_upload:
            instance.upload_doc(doc_dict=files_to_upload)
            instance.refresh_from_db()
            updated_serializer = self.get_serializer(instance)
            new_data = updated_serializer.data
        else:
            new_data = serializer.data

        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="ManualWeightEntry",
            description=f"Updated Manual Weight Entry for vehicle: {instance.vehicle_no}",
            request=request,
            payload={
                "old_data": clean_payload(old_data),
                "new_data": clean_payload(new_data),
            },
        )

        return Response(
            {
                "success": True,
                "message": "Updated successfully",
                "data": new_data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="purchasers")
    def purchasers_list(self, request):
        users = User.objects.filter(
            usergroupsmodel__group__name="Purchaser", is_active=True, deleted=False
        ).values("id", "first_name", "last_name", "email")
        data = [
            {
                "id": u["id"],
                "name": f"{u['first_name']} {u['last_name']}".strip() or u["email"],
            }
            for u in users
        ]
        page = self.paginate_queryset(data)

        if page is not None:
            return self.get_paginated_response({"success": True, "data": page})

        return Response(
            {
                "count": len(data),
                "next": None,
                "privious": None,
                "results": {"success": True, "data": data},
            }
        )

    @action(detail=False, methods=["get"], url_path="sellers")
    def seller_list(self, request):
        users = User.objects.filter(
            usergroupsmodel__group__name="Seller", is_active=True, deleted=False
        ).values("id", "first_name", "last_name", "email")

        data = [
            {
                "id": u["id"],
                "name": f"{u['first_name']} {u['last_name']}".strip() or u["email"],
            }
            for u in users
        ]
        page = self.paginate_queryset(data)

        if page is not None:
            return self.get_paginated_response({"success": True, "data": page})

        return Response(
            {
                "count": len(data),
                "next": None,
                "privious": None,
                "results": {"success": True, "data": data},
            }
        )
