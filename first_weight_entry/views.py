import json
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from utils.log_activity import clean_payload, log_user_activity
from common.models import ArchiveMixin
from .models import FirstWeightEntry
from .serializer import FirstWeightEntrySerializer
from common.master_views import BaseModelViewSet

User = get_user_model()


class FirstWeightEntryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = FirstWeightEntry.objects.all().select_related(
        "vehicle_no", "party_name", "vehicle_type"
    )
    serializer_class = FirstWeightEntrySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    search_fields = BaseModelViewSet.serching_fields + [
        "id",
        "weight_for",
        "weight_automatic",
        "gross_weight",
        "tare_weight",
        "net_weight",
        "date_time_first",
        "date_time_second",
        "mound",
        "serial_no",
        "total_copy",
        "is_second_entry_done",
        "cash_party_name",
        "party_mobile_no",
        "party_name__party_name",
        "vehicle_type__vehicle_type",
        "material__item_name",
    ]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "id",
        "weight_for",
        "weight_automatic",
        "gross_weight",
        "tare_weight",
        "net_weight",
        "date_time_first",
        "date_time_second",
        "mound",
        "serial_no",
        "total_copy",
        "vehicle_no",
        "vehicle_no_display",
        "cash_party_name",
        "party_mobile_no",
        "party_name",
        "vehicle_type",
        "material",
        "purchaser",
        "seller",
        "is_second_entry_done",
        "party_name_display",
        "vehicle_type_name",
        "material_name",
        "purchaser_name",
    ]

    def create(self, request, *args, **kwargs):
        data = {}

        if "data" in request.POST:
            try:
                data = json.loads(request.POST.get("data", "{}"))
            except:
                return Response(
                    {"success": False, "message": "Invalid JSON in data"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        data.pop("capture_photo", None)

        files_to_upload = {}
        for field in ["capture_photo", "capture_photo_2"]:
            if field in request.FILES:
                files_to_upload[field] = request.FILES[field]
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user)

        if files_to_upload:
            instance.upload_doc(doc_dict=files_to_upload)
            instance.refresh_from_db()
            serializer = self.get_serializer(instance)

        log_user_activity(
            user=request.user,
            action="CREATE",
            module_name="FirstWeightEntry",
            description=f"Created First Weight Entry for vehicle: {instance.vehicle_no}",
            request=request,
            payload=clean_payload(serializer.data),
        )

        return Response(
            {
                "success": True,
                "message": "Created successfully",
                "data": serializer.data,
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
        for field in ["capture_photo", "capture_photo_2"]:
            if field in request.FILES:
                files_to_upload[field] = request.FILES[field]
            data.pop(field, None)

        clear_fields = []

        for field in ["capture_photo", "capture_photo_2"]:
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

        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="FirstWeightEntry",
            description=f"Updated First Weight Entry for vehicle: {instance.vehicle_no}",
            request=request,
            payload={
                "old_data": clean_payload(old_data),
                "new_data": clean_payload(updated_serializer.data),
            },
        )

        return Response(
            {
                "success": True,
                "message": "Updated successfully",
                "data": updated_serializer.data,
            }
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
