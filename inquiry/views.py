import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin, FinancialYearModel, JobWorkType
from inquiry.models import Inquiry, InquiryDetail, InquiryDetailDrawing
from inquiry.serializers import (
    InquiryCreateSerializer,
    InquiryDetailCreateSerializer,
    InquiryDetailSerializer,
    InquiryListSerializer,
    InquirySerializer,
)
from inquiry_quotation.models import InquiryQuotation, InquiryQuotationDetail
from inquiry_quotation.serializers import InquiryQuotationSerializer
from utils.generate_number import (
    generate_inquiry_number,
    generate_inquiry_quotation_number,
)
from utils.log_activity import clean_payload, log_user_activity
from rest_framework.permissions import AllowAny


def get_indexed_files(request_files, key_prefix):
    """Collect files sent as key_prefix[0], key_prefix[1], ..."""
    files = []
    for key in request_files.keys():
        if key.startswith(f"{key_prefix}["):
            files.append(request_files[key])
    return files


class InquiryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = Inquiry.objects.select_related(
        "created_by", "updated_by", "assigned_user"
    ).prefetch_related(
        Prefetch(
                "inquiry_details", queryset=InquiryDetail.objects.select_related(
                "alloy", "temper"
            ).prefetch_related("surface_finish")
        ),
    ).all()
    serializer_class = InquirySerializer
    permission_classes = [AllowAny]
    list_serializer_class = InquiryListSerializer

    search_fields = [
        "inquiry_number",
        "status",
        "customer_name",
        "contact_persons",
        "initial_requirement",
        "annual_requirement",
        "inquiry_source",
        "assigned_user__first_name",
        "assigned_user__last_name",
        "assigned_user__email",
        "created_by__first_name",
        "created_by__last_name",
        "created_by__email",
        "updated_by__first_name",
        "updated_by__last_name",
        "updated_by__email",
    ]
    ordering_fields = [
        "inquiry_number",
        "status",
        "customer_name",
        "inquiry_date",
        "created_at",
        "updated_at",
        "assigned_user__first_name",
    ]

    def get_queryset(self):
        qs = (
                Inquiry.objects.select_related(
                    "created_by", "updated_by", "assigned_user"
            ).all().order_by("-created_at")
        )
        user = self.request.user
        if self.action == "list":
            qs = qs.filter(deleted=False)
        elif self.action == "archive_list":
            qs = qs.filter(deleted=True)    
        # Super Admin -> All Records
        if user.is_superuser:
            return qs

        # Users having Inquiry View Permission -> All Records
        if user.has_perm("inquiry.view_inquiry"):
            return qs

        # Assigned User -> Only Assigned Records
        return qs.filter(assigned_user=user)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        
        try:
            user = request.user if request.user.is_authenticated else None
            data_str = request.data.get("data")
            if data_str:
                try:
                    json_data = json.loads(data_str)
                except json.JSONDecodeError:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid JSON format in 'data' field.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                inquiry_details_data = json_data.pop("inquiry_details", [])

                source_attachment_file = request.FILES.get("source_attachment")

                serializer = InquiryCreateSerializer(
                    data=json_data, context={"request": request}
                )

                if serializer.is_valid():
                    with transaction.atomic():
                        inquiry_number = generate_inquiry_number()

                        inquiry = serializer.save(
                            inquiry_number=inquiry_number,
                            inquiry_date=timezone.now(),
                            created_by=user,
                            updated_by=user,
                        )
                        if source_attachment_file:
                            inquiry.upload_doc(
                                {"source_attachment": source_attachment_file}
                            )

                        detail_objects = []
                        for idx, detail_data in enumerate(inquiry_details_data):
                            detail_obj = InquiryDetail(
                                inquiry=inquiry,
                                section_no=detail_data.get("section_no"),
                                description=detail_data.get("description"),
                                standard_confirmation=detail_data.get(
                                    "standard_confirmation"
                                ),
                                standard_confirmation_other=detail_data.get(
                                    "standard_confirmation_other"
                                ),
                                alloy_id=detail_data.get("alloy"),
                                temper_id=detail_data.get("temper"),
                                length=detail_data.get("length"),
                                tolerance=detail_data.get("tolerance"),
                                tolerance_plus=detail_data.get("tolerance_plus"),
                                tolerance_minus=detail_data.get("tolerance_minus"),
                                out_source=detail_data.get("out_source", False),
                                cutting=detail_data.get("cutting", False),
                                machining=detail_data.get("machining", False),
                                deburring=detail_data.get("deburring", False),
                                cutting_price=detail_data.get("cutting_price"),
                                machining_price=detail_data.get("machining_price"),
                                deburring_price=detail_data.get("deburring_price"),
                                anodising=detail_data.get("anodising", False),
                                powder_coating=detail_data.get("powder_coating", False),
                                pvdf=detail_data.get("pvdf", False),
                                anodising_price=detail_data.get("anodising_price"),
                                anodising_description=detail_data.get(
                                    "anodising_description"
                                ),
                                powder_coating_price=detail_data.get(
                                    "powder_coating_price"
                                ),
                                powder_coating_description=detail_data.get(
                                    "powder_coating_description"
                                ),
                                pvdf_price=detail_data.get("pvdf_price"),
                                pvdf_description=detail_data.get("pvdf_description"),
                                laser_marking_price=detail_data.get(
                                    "laser_marking_price"
                                ),
                                laser_marking_description=detail_data.get(
                                    "laser_marking_description"
                                ),
                                post_operation=detail_data.get("post_operation"),
                                post_operation_other=detail_data.get(
                                    "post_operation_other"
                                ),
                                end_application=detail_data.get("end_application"),
                                created_by=user,
                                updated_by=user,
                            )
                            detail_obj.save()
                            try:
                                drawing_files_for_detail = get_indexed_files(request.FILES, f"drawing_attachment_{idx}")
                                if drawing_files_for_detail:
                                    detail_obj.upload_drawings(drawing_files_for_detail)
                            except ValidationError as e:
                                return Response(
                                    {
                                        "success": False,
                                        "message": f"Drawing upload failed for section {detail_data.get('section_no')}.",
                                        "errors": e.message_dict,
                                    },
                                    status=400,
                                )
                            surface_items = detail_data.get("surface_finish", [])
                            if surface_items:
                                detail_obj.surface_finish.set(surface_items)
                            detail_objects.append(detail_obj)
                        created_details = InquiryDetail.objects.bulk_create(
                            detail_objects, batch_size=1000, ignore_conflicts=True
                        )
                        response_data = {
                            "id": inquiry.id,
                            "inquiry_number": inquiry.inquiry_number,
                            "customer_name": inquiry.customer_name,
                            "status": inquiry.status,
                            "created_at": inquiry.created_at.isoformat(),
                            "details_count": len(created_details),
                            "data": serializer.data,
                        }
                        try:
                            log_user_activity(
                                user=request.user,
                                action="CREATE",
                                module_name="Inquiry",
                                description=f"Created Inquiry with {len(created_details)} details",
                                request=request,
                                payload={},
                            )
                        except:
                            pass

                    return Response(
                        {
                            "success": True,
                            "message": "Inquiry created successfully with inquiry details.",
                            "data": response_data,
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid inquiry data provided.",
                            "errors": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid():
                    with transaction.atomic():
                        inquiry_number = generate_inquiry_number()

                        inquiry = serializer.save(
                            inquiry_number=inquiry_number,
                            created_by=user,
                            updated_by=user,
                        )
                        payload = clean_payload(request.data)

                        response_data = {
                            "id": inquiry.id,
                            "inquiry_number": inquiry.inquiry_number,
                            "customer_name": inquiry.customer_name,
                            "status": inquiry.status,
                            "created_at": inquiry.created_at.isoformat(),
                        }
                        try:
                            log_user_activity(
                                user=user,
                                action="CREATE",
                                module_name="Inquiry",
                                description=f"Created Inquiry",
                                request=request,
                                payload={},
                            )
                        except:
                            pass

                    return Response(
                        {
                            "success": True,
                            "message": "Inquiry created successfully.",
                            "data": response_data,
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid data provided.",
                            "errors": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "message": "File upload failed.",
                    "errors": e.message_dict if hasattr(e, "message_dict") else {"error": e.messages},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating inquiry: {str(e)}",
                    "errors": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            old_status = instance.status
            data_str = request.data.get("data")

            if data_str:
                try:
                    json_data = json.loads(data_str)
                except json.JSONDecodeError:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid JSON format in 'data' field.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                inquiry_details_data = json_data.pop("inquiry_details", [])
                source_attachment_file = request.FILES.get("source_attachment")

                drawing_files = {}
                for idx, detail_data in enumerate(inquiry_details_data):
                    if get_indexed_files(request.FILES, f"drawing_attachment_{idx}"):
                        drawing_files[idx] = True

                serializer = self.get_serializer(instance, data=json_data, partial=True)

                if serializer.is_valid():
                    with transaction.atomic():
                        inquiry = serializer.save(updated_by=request.user)
                        if source_attachment_file:
                            inquiry.upload_doc(
                                {"source_attachment": source_attachment_file}
                            )

                        created_details = []

                        for idx, detail_data in enumerate(inquiry_details_data):
                            if "id" in detail_data and detail_data["id"]:
                                detail_obj = InquiryDetail.objects.get(
                                    id=detail_data["id"]
                                )

                                detail_serializer = InquiryDetailCreateSerializer(
                                    detail_obj, data=detail_data, partial=True
                                )

                                if detail_serializer.is_valid():
                                    updated_detail = detail_serializer.save(
                                        updated_by=request.user
                                    )

                                    remove_ids = [
                                        int(i) for i in detail_data.get("remove_drawing_ids", [])
                                        if str(i).isdigit()
                                    ]
                                    if remove_ids:
                                        InquiryDetailDrawing.objects.filter(
                                            id__in=remove_ids,
                                            inquiry_detail=updated_detail
                                        ).delete()

                                    surface_items = detail_data.get(
                                        "surface_finish", []
                                    )
                                    updated_detail.surface_finish.set(
                                        surface_items if surface_items else []
                                    )
                                    if surface_items:
                                        selected_jobwork_names = set(
                                            JobWorkType.objects.filter(
                                                id__in=surface_items
                                            ).values_list("name", flat=True)
                                        )

                                        selected_names_lower = {
                                            name.lower()
                                            for name in selected_jobwork_names
                                        }

                                        if "cutting" not in detail_data:
                                            updated_detail.cutting = any(
                                                "cutting" in name_lower
                                                for name_lower in selected_names_lower
                                            )
                                        if "machining" not in detail_data:
                                            updated_detail.machining = any(
                                                "machining" in name_lower
                                                for name_lower in selected_names_lower
                                            )
                                        if "deburring" not in detail_data:
                                            updated_detail.deburring = any(
                                                "deburring" in name_lower
                                                for name_lower in selected_names_lower
                                            )
                                        if "out_source" not in detail_data:
                                            updated_detail.out_source = any(
                                                "out source" in name_lower
                                                or "outsource" in name_lower
                                                for name_lower in selected_names_lower
                                            )
                                        if "anodising" not in detail_data:
                                            updated_detail.anodising = any(
                                                "anodising" in name_lower
                                                or "anodizing" in name_lower
                                                for name_lower in selected_names_lower
                                            )
                                        if "powder_coating" not in detail_data:
                                            updated_detail.powder_coating = any(
                                                "powder coating" in name_lower
                                                or "powder_coating" in name_lower
                                                or "powdercoating" in name_lower
                                                for name_lower in selected_names_lower
                                            )
                                        if "pvdf" not in detail_data:
                                            updated_detail.pvdf = any(
                                                "pvdf" in name_lower
                                                for name_lower in selected_names_lower
                                            )
                                    else:
                                        if "cutting" not in detail_data:
                                            updated_detail.cutting = False
                                        if "machining" not in detail_data:
                                            updated_detail.machining = False
                                        if "deburring" not in detail_data:
                                            updated_detail.deburring = False
                                        if "out_source" not in detail_data:
                                            updated_detail.out_source = False
                                        if "anodising" not in detail_data:
                                            updated_detail.anodising = False
                                        if "powder_coating" not in detail_data:
                                            updated_detail.powder_coating = False
                                        if "pvdf" not in detail_data:
                                            updated_detail.pvdf = False

                                    if "cutting" in detail_data:
                                        updated_detail.cutting = bool(
                                            detail_data.get("cutting", False)
                                        )
                                    if "machining" in detail_data:
                                        updated_detail.machining = bool(
                                            detail_data.get("machining", False)
                                        )
                                    if "deburring" in detail_data:
                                        updated_detail.deburring = bool(
                                            detail_data.get("deburring", False)
                                        )
                                    if "out_source" in detail_data:
                                        updated_detail.out_source = bool(
                                            detail_data.get("out_source", False)
                                        )
                                    if "anodising" in detail_data:
                                        updated_detail.anodising = bool(
                                            detail_data.get("anodising", False)
                                        )
                                    if "powder_coating" in detail_data:
                                        updated_detail.powder_coating = bool(
                                            detail_data.get("powder_coating", False)
                                        )
                                    if "pvdf" in detail_data:
                                        updated_detail.pvdf = bool(
                                            detail_data.get("pvdf", False)
                                        )

                                    drawing_files_for_detail = get_indexed_files(request.FILES, f"drawing_attachment_{idx}")
                                    if drawing_files_for_detail:
                                        updated_detail.upload_drawings(drawing_files_for_detail)

                                    updated_detail.save()
                                else:
                                    return Response(
                                        {
                                            "success": False,
                                            "message": f"Invalid inquiry detail data at index {idx}.",
                                            "errors": detail_serializer.errors,
                                        },
                                        status=status.HTTP_400_BAD_REQUEST,
                                    )
                                continue

                            detail_serializer = InquiryDetailCreateSerializer(
                                data=detail_data
                            )
                            if detail_serializer.is_valid():
                                inquiry_detail = detail_serializer.save(
                                    inquiry=inquiry,
                                    created_by=request.user,
                                    updated_by=request.user,
                                )

                                surface_items = detail_data.get("surface_finish", [])
                                if surface_items:
                                    inquiry_detail.surface_finish.set(surface_items)

                                drawing_files_for_detail = get_indexed_files(request.FILES, f"drawing_attachment_{idx}")
                                if drawing_files_for_detail:
                                    inquiry_detail.upload_drawings(drawing_files_for_detail)

                                created_details.append(inquiry_detail)
                            else:
                                return Response(
                                    {
                                        "success": False,
                                        "message": f"Invalid inquiry detail data at index {idx}.",
                                        "errors": detail_serializer.errors,
                                    },
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                        inquiry.refresh_from_db()
                        response_serializer = InquirySerializer(inquiry)
                        log_user_activity(
                            user=request.user,
                            action="UPDATE",
                            module_name="Inquiry",
                            description=f"Updated Inquiry and added {len(created_details)} details",
                            request=request,
                            payload=json_data,
                        )

                    return Response(
                        {
                            "success": True,
                            "message": "Inquiry updated successfully with inquiry details.",
                            "data": response_serializer.data,
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid inquiry data provided.",
                            "errors": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            else:
                source_attachment_file = request.FILES.get("source_attachment")
                data = request.data.copy()

                remove_file = (
                    data.get("source_attachment") in ["", "null", None]
                    and "source_attachment" in data
                )

                if "source_attachment" in data and source_attachment_file:
                    data.pop("source_attachment")
                elif "source_attachment" in data:
                    data.pop("source_attachment")

                serializer = self.get_serializer(instance, data=data, partial=True)
                if serializer.is_valid():
                    with transaction.atomic():
                        inquiry = serializer.save(updated_by=request.user)
                        new_status = inquiry.status

                        if source_attachment_file:
                            inquiry.upload_doc(
                                {"source_attachment": source_attachment_file}
                            )
                        elif remove_file:
                            if inquiry.source_attachment and hasattr(
                                inquiry.source_attachment, "delete"
                            ):
                                inquiry.source_attachment.delete(save=False)
                            inquiry.source_attachment = None
                            inquiry.save()

                        inquiry.refresh_from_db()
                        payload = clean_payload(request.data)

                        log_user_activity(
                            user=request.user,
                            action="UPDATE",
                            module_name="Inquiry",
                            description=f"Updated Inquiry",
                            request=request,
                            payload=payload,
                        )
                        response_serializer = self.get_serializer(inquiry)

                    return Response(
                        {
                            "success": True,
                            "message": "Inquiry updated successfully.",
                            "data": response_serializer.data,
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid data provided.",
                            "errors": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating inquiry: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["patch"], url_path="regret")
    def regret_inquiry(self, request, pk=None):
        try:
            inquiry = self.get_object()

            if inquiry.status == "Quotation":
                return Response(
                    {
                        "success": False,
                        "message": "You can not Regret this inquiry because Quotation is generated.",
                    }
                )
            if inquiry.status == "SalesOrder":
                return Response(
                    {
                        "success": False,
                        "message": "You can not Regret this inquiry because SalesOrder is generated.",
                    }
                )

            regret_reason = request.data.get("regret_reason")
            new_status = request.data.get("status", "Regretted")

            if not regret_reason or not regret_reason.strip():
                return Response(
                    {
                        "success": False,
                        "message": "Regret Reason is Compulsory.",
                        "errors": {"regret_reason": ["This field is required."]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            inquiry.status = new_status
            inquiry.regret_reason = regret_reason.strip()
            inquiry.updated_by = request.user
            inquiry.updated_at = timezone.now()
            inquiry.save(
                update_fields=["status", "regret_reason", "updated_by", "updated_at"]
            )

            try:
                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="Inquiry",
                    description=f"Inquiry {inquiry.inquiry_number} marked as Regretted. Reason: {regret_reason}",
                    request=request,
                    payload={"regret_reason": regret_reason},
                )
            except:
                pass

            serializer = InquiryListSerializer(inquiry)
            return Response(
                {
                    "success": True,
                    "message": "Inquiry successfully marked as Regretted.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Inquiry.DoesNotExist:
            return Response(
                {"success": False, "message": "Inquiry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["patch"], url_path="feasible")
    def feasible(self, request, pk=None):
        try:
            inquiry = self.get_object()
            if inquiry.status == "Quotation":
                return Response(
                    {
                        "success": False,
                        "message": "You can not Feasible this inquiry because Quotation is generated.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if inquiry.status == "SalesOrder":
                return Response(
                    {
                        "success": False,
                        "message": "You can not Feasible this inquiry because SalesOrder is generated.",
                    }
                )

            feasible_description = request.data.get("feasible_description")
            feasible_attachment = request.FILES.get("feasible_attachment")

            if not feasible_description or not feasible_description.strip():
                return Response(
                    {
                        "success": False,
                        "message": "Feasible Description is Compulsory.",
                        "errors": {"feasible_description": ["This field is required."]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                inquiry.feasiblity_description = feasible_description.strip()
                inquiry.status = "Feasible"
                inquiry.updated_by = request.user
                inquiry.updated_at = timezone.now()

                max_size_override = {"feasiblity_attachment": 5 * 1024 * 1024}

                inquiry.upload_doc(
                    doc_dict={"feasiblity_attachment": feasible_attachment},
                    max_size_override=max_size_override,
                )

                inquiry.save()

            except ValidationError as e:
                return Response(
                    {
                        "success": False,
                        "message": "File upload failed.",
                        "errors": (
                            e.message_dict
                            if hasattr(e, "message_dict")
                            else {"upload_errors": e.messages}
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                return Response(
                    {"success": False, "message": f"File processing error: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            try:
                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="Inquiry",
                    description=f"Inquiry {inquiry.inquiry_number} marked as Feasible. Description: {feasible_description[:50]}...",
                    request=request,
                    payload={
                        "feasible_description": feasible_description,
                        "feasible_attachment": inquiry.feasiblity_attachment,
                    },
                )
            except:
                pass

            serializer = InquiryListSerializer(inquiry)
            return Response(
                {
                    "success": True,
                    "message": "Inquiry successfully marked as Feasible.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Inquiry.DoesNotExist:
            return Response(
                {"success": False, "message": "Inquiry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="assign")
    def assign_user(self, request, pk=None):
        try:
            inquiry = self.get_object()

            if inquiry.status == "Quotation":
                return Response(
                    {
                        "success": False,
                        "message": "You can not assign user to this inquiry because Quotation is generated.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if inquiry.status == "SalesOrder":
                return Response(
                    {
                        "success": False,
                        "message": "You can not assign user to this inquiry because SalesOrder is generated.",
                    }
                )

            assigned_user_id = request.data.get("assigned_user_id")
            if not assigned_user_id:
                return Response(
                    {"success": False, "message": "assigned_user_id is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            User = get_user_model()
            try:
                assigned_user = User.objects.get(id=assigned_user_id)
            except User.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": f"User with ID {assigned_user_id} not found.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            with transaction.atomic():
                inquiry.assigned_user = assigned_user
                inquiry.updated_by = request.user
                inquiry.status = "Assigned"
                inquiry.save()

                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="Inquiry",
                    description=f"Assigned user {assigned_user.get_full_name()} to Inquiry {inquiry.inquiry_number}",
                    request=request,
                    payload={"assigned_user_id": assigned_user_id},
                )

            serializer = self.get_serializer(inquiry)
            response_data = {
                "success": True,
                "message": f"Inquiry {inquiry.inquiry_number} assigned to User {assigned_user.get_full_name()} successfully.",
                "data": {
                    "inquiry": serializer.data,
                    "assigned_user": {
                        "id": assigned_user.id,
                        "name": assigned_user.get_full_name() or assigned_user.username,
                    },
                },
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "message": f"{str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="convert-to-quotation")
    def convert_to_quotation(self, request, pk=None):
        try:
            inquiry_id = pk
            quotation_details_data = request.data.get("quotation_details", [])
            terms_and_condition = request.data.get("terms_and_condition", "")
            remarks = request.data.get("remarks", "")

            try:
                inquiry = Inquiry.objects.get(id=inquiry_id, deleted=False)
            except Inquiry.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": f"Inquiry with ID {inquiry_id} not found.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not quotation_details_data:
                return Response(
                    {"success": False, "message": "quotation_details are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                quotation_no = generate_inquiry_quotation_number()

                inquiry_quotation = InquiryQuotation.objects.create(
                    inquiry=inquiry,
                    quotation_no=quotation_no,
                    terms_and_condition=terms_and_condition,
                    remarks=remarks,
                    status="Quotation",
                    created_by=request.user,
                    updated_by=request.user,
                )

                created_details = []
                for detail_data in quotation_details_data:
                    inquiry_detail_id = detail_data.get("id")
                    if inquiry_detail_id:
                        try:
                            inquiry_detail = InquiryDetail.objects.get(
                                id=inquiry_detail_id, inquiry=inquiry, deleted=False
                            )
                        except InquiryDetail.DoesNotExist:
                            return Response(
                                {
                                    "success": False,
                                    "message": f"InquiryDetail with ID {inquiry_detail_id} not found for this inquiry.",
                                },
                                status=status.HTTP_404_NOT_FOUND,
                            )

                    surface_finish_ids = detail_data.pop("surface_finish", [])
                    detail_data.pop("id", None)

                    quotation_detail = InquiryQuotationDetail.objects.create(
                        inquiry_quotation=inquiry_quotation,
                        section_no=detail_data.get("section_no"),
                        alloy_id=detail_data.get("alloy"),
                        temper_id=detail_data.get("temper"),
                        length=detail_data.get("length"),
                        price_per_kg=detail_data.get("price_per_kg"),
                        conversion=detail_data.get("conversion"),
                        packing_cost=detail_data.get("packing_cost"),
                        net_weight=detail_data.get("net_weight"),
                        quantity=detail_data.get("quantity"),
                        out_source=detail_data.get("out_source", False),
                        cutting=detail_data.get("cutting", False),
                        machining=detail_data.get("machining", False),
                        deburring=detail_data.get("deburring", False),
                        cutting_price=detail_data.get("cutting_price"),
                        machining_price=detail_data.get("machining_price"),
                        deburring_price=detail_data.get("deburring_price"),
                        anodising=detail_data.get("anodising", False),
                        powder_coating=detail_data.get("powder_coating", False),
                        pvdf=detail_data.get("pvdf", False),
                        anodising_price=detail_data.get("anodising_price"),
                        anodising_description=detail_data.get("anodising_description"),
                        powder_coating_price=detail_data.get("powder_coating_price"),
                        powder_coating_description=detail_data.get(
                            "powder_coating_description"
                        ),
                        pvdf_price=detail_data.get("pvdf_price"),
                        pvdf_description=detail_data.get("pvdf_description"),
                        laser_marking_price=detail_data.get("laser_marking_price"),
                        laser_marking_description=detail_data.get(
                            "laser_marking_description"
                        ),
                        created_by=request.user,
                        updated_by=request.user,
                    )

                    if surface_finish_ids:
                        quotation_detail.surface_finish.set(surface_finish_ids)

                    created_details.append(quotation_detail)

                inquiry.status = "Quotation"
                inquiry.updated_by = request.user
                inquiry.save()

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="CREATE",
                    module_name="InquiryQuotation",
                    description=f"Converted Inquiry {inquiry.inquiry_number} to InquiryQuotation {quotation_no} with {len(created_details)} details",
                    request=request,
                    payload=payload,
                )

                response_serializer = InquiryQuotationSerializer(inquiry_quotation)
                return Response(
                    {
                        "success": True,
                        "message": f"Inquiry successfully converted to Quotation. Quotation Number: {quotation_no}",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error converting inquiry to quotation: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InquiryDetailViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = InquiryDetail.objects.all()
    serializer_class = InquiryDetailSerializer

    search_fields = [
        "section_no",
        "description",
        "end_application",
        "post_operation",
        "standard_confirmation",
        "tolerance",
        "alloy__name",
        "temper__name",
        "inquiry__inquiry_number",
        "inquiry__customer_name",
        "created_by__first_name",
        "created_by__last_name",
        "created_by__email",
        "updated_by__first_name",
        "updated_by__last_name",
        "updated_by__email",
    ]
    ordering_fields = [
        "section_no",
        "created_at",
        "updated_at",
        "length",
        "inquiry__inquiry_number",
        "alloy__name",
        "temper__name",
    ]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return InquiryDetailCreateSerializer
        return InquiryDetailSerializer

    def get_queryset(self):
        return (
            InquiryDetail.objects.filter(deleted=False)
            .select_related(
                "created_by",
                "updated_by",
                "deleted_by",
                "alloy",
                "temper",
                "inquiry",
                "inquiry__created_by",
                "inquiry__updated_by",
            )
            .prefetch_related("surface_finish")
            .order_by("-id")
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    inquiry_detail = serializer.save(
                        created_by=request.user, updated_by=request.user
                    )
                    drawing_files = get_indexed_files(request.FILES, "drawing_attachment")
                    if drawing_files:
                        try:
                            inquiry_detail.upload_drawings(drawing_files)
                        except ValidationError as e:
                            return Response(
                                {
                                    "success": False,
                                    "message": "Drawing attachment upload failed.",
                                    "errors": (
                                        e.message_dict
                                        if hasattr(e, "message_dict")
                                        else {"upload_errors": e.messages}
                                    ),
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="CREATE",
                        module_name="InquiryDetail",
                        description=f"InquiryDetail Inquiry",
                        request=request,
                        payload=payload,
                    )
                    response_serializer = self.get_serializer(inquiry_detail)

                return Response(
                    {
                        "success": True,
                        "message": "Inquiry detail created successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid data provided.",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating inquiry detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            drawing_attachment_files = get_indexed_files(request.FILES, "drawing_attachment")
            data = request.data.copy()

            remove_drawing_ids = [
                int(i) for i in (
                    request.data.getlist("remove_drawing_ids[]")
                    or request.data.getlist("remove_drawing_ids")
                ) if str(i).isdigit()
            ]

            if "drawing_attachment" in data:
                data.pop("drawing_attachment")

            serializer = self.get_serializer(instance, data=data, partial=True)
            if serializer.is_valid():
                with transaction.atomic():
                    inquiry_detail = serializer.save(updated_by=request.user)

                    if remove_drawing_ids:
                        InquiryDetailDrawing.objects.filter(
                            id__in=remove_drawing_ids,
                            inquiry_detail=inquiry_detail
                        ).delete()

                    if drawing_attachment_files:
                        inquiry_detail.upload_drawings(drawing_attachment_files)
                    inquiry_detail.refresh_from_db()

                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="UPDATE",
                        module_name="InquiryDetail",
                        description=f"InquiryDetail Updated.",
                        request=request,
                        payload=payload,
                    )
                    response_serializer = self.get_serializer(inquiry_detail)

                return Response(
                    {
                        "success": True,
                        "message": "Inquiry detail updated successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid data provided.",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating inquiry detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
