import csv
import logging
from io import StringIO
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from product.models import Alloy
from product.serializers import AlloyDropdownSerializer, AlloyListSerializers, AlloySerializers
from utils.custom_filters import CustomSearchFilter
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class AlloyViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Alloy.objects.all().select_related(
            "created_by", "updated_by", "deleted_by", "standard")
    )
    serializer_class = AlloySerializers
    permission_classes = [AllowAny]
    # list_serializer_class = AlloyListSerializers
    fy_filtering_enabled = False

    search_fields = [
        "id",
        "alloy_code",
        "color_code",
        "si_min",
        "si_max",
        "mg_min",
        "mg_max",
        "fe_min",
        "fe_max",
        "mn_min",
        "mn_max",
        "cu_min",
        "cu_max",
        "zn_min",
        "zn_max",
        "cr_min",
        "cr_max",
        "ti_min",
        "ti_max",
        "bi_min",
        "bi_max",
        "pb_min",
        "pb_max",
        "sn_min",
        "sn_max",
        "others_each_min",
        "others_each_max",
        "others_total_min",
        "others_total_max",
        "al_min",
        "al_max",
        "remark",
        "deleted",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "created_at",
        "updated_at",
    ]

    ordering_fields = [
        "id",
        "alloy_code",
        "color_code",
        "si_min",
        "si_max",
        "mg_min",
        "mg_max",
        "fe_min",
        "fe_max",
        "mn_min",
        "mn_max",
        "cu_min",
        "cu_max",
        "zn_min",
        "zn_max",
        "cr_min",
        "cr_max",
        "ti_min",
        "ti_max",
        "bi_min",
        "bi_max",
        "pb_min",
        "pb_max",
        "sn_min",
        "sn_max",
        "others_each_min",
        "others_each_max",
        "others_total_min",
        "others_total_max",
        "al_min",
        "al_max",
        "remark",
        "deleted",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "created_at",
        "updated_at",
    ]

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            alloy_code = data.get("alloy_code", "").strip()
            standard_id = data.get("standard")

            if not all([alloy_code]):
                return Response(
                    {
                        "success": False,
                        "message": "alloy_code is required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Alloy.objects.filter(
                alloy_code__iexact=alloy_code,
                standard_id=standard_id,
                deleted=False,
            ).exists():
                return Response(
                    {"success": False, "message": "This alloy already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from decimal import Decimal

            min_max_pairs = [
                ("si_min", "si_max", "Si"),
                ("mg_min", "mg_max", "Mg"),
                ("fe_min", "fe_max", "Fe"),
                ("mn_min", "mn_max", "Mn"),
                ("cu_min", "cu_max", "Cu"),
                ("zn_min", "zn_max", "Zn"),
                ("cr_min", "cr_max", "Cr"),
                ("ti_min", "ti_max", "Ti"),
                ("bi_min", "bi_max", "Bi"),
                ("pb_min", "pb_max", "Pb"),
                ("sn_min", "sn_max", "Sn"),
                ("others_each_min", "others_each_max", "Others Each"),
                ("others_total_min", "others_total_max", "Others Total"),
            ]

            for min_field, max_field, field_name in min_max_pairs:
                min_val = data.get(min_field)
                max_val = data.get(max_field)
                if min_val is not None and max_val is not None:
                    try:
                        min_dec = Decimal(str(min_val))
                        max_dec = Decimal(str(max_val))
                        if min_dec > max_dec:
                            return Response(
                                {
                                    "success": False,
                                    "message": f"{field_name} Min cannot be greater than Max.",
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    except (ValueError, TypeError):
                        pass

            payload = {
                "si_min": data.get("si_min"),
                "si_max": data.get("si_max"),
                "mg_min": data.get("mg_min"),
                "mg_max": data.get("mg_max"),
                "fe_min": data.get("fe_min"),
                "fe_max": data.get("fe_max"),
                "mn_min": data.get("mn_min"),
                "mn_max": data.get("mn_max"),
                "cu_min": data.get("cu_min"),
                "cu_max": data.get("cu_max"),
                "zn_min": data.get("zn_min"),
                "zn_max": data.get("zn_max"),
                "cr_min": data.get("cr_min"),
                "cr_max": data.get("cr_max"),
                "ti_min": data.get("ti_min"),
                "ti_max": data.get("ti_max"),
                "bi_min": data.get("bi_min"),
                "bi_max": data.get("bi_max"),
                "pb_min": data.get("pb_min"),
                "pb_max": data.get("pb_max"),
                "sn_min": data.get("sn_min"),
                "sn_max": data.get("sn_max"),
                "others_each_min": data.get("others_each_min"),
                "others_each_max": data.get("others_each_max"),
                "others_total_min": data.get("others_total_min"),
                "others_total_max": data.get("others_total_max"),
            }

            def _has_any(fields) -> bool:
                for f in fields:
                    v = payload.get(f)
                    if v is None:
                        continue
                    if isinstance(v, str) and v.strip() == "":
                        continue
                    return True
                return False

            has_min_values = _has_any(Alloy.AL_COMPONENT_MIN_FIELDS)
            has_max_values = _has_any(Alloy.AL_COMPONENT_MAX_FIELDS)

            if has_min_values:
                sum_min = sum(
                    (Decimal(str(payload.get(f) or 0)))
                    for f in Alloy.AL_COMPONENT_MIN_FIELDS
                )
                if sum_min > Decimal("100"):
                    return Response(
                        {
                            "success": False,
                            "message": "Sum of all Min fields cannot exceed 100.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if has_max_values:
                sum_max = sum(
                    (Decimal(str(payload.get(f) or 0)))
                    for f in Alloy.AL_COMPONENT_MAX_FIELDS
                )
                if sum_max > Decimal("100"):
                    return Response(
                        {
                            "success": False,
                            "message": "Sum of all Max fields cannot exceed 100.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            alloy = Alloy.objects.create(
                alloy_code=alloy_code,
                color_code=data.get("color_code"),
                standard_id=data.get("standard"),
                si_min=data.get("si_min"),
                si_max=data.get("si_max"),
                mg_min=data.get("mg_min"),
                mg_max=data.get("mg_max"),
                fe_min=data.get("fe_min"),
                fe_max=data.get("fe_max"),
                mn_min=data.get("mn_min"),
                mn_max=data.get("mn_max"),
                cu_min=data.get("cu_min"),
                cu_max=data.get("cu_max"),
                zn_min=data.get("zn_min"),
                zn_max=data.get("zn_max"),
                cr_min=data.get("cr_min"),
                cr_max=data.get("cr_max"),
                ti_min=data.get("ti_min"),
                ti_max=data.get("ti_max"),
                bi_min=data.get("bi_min"),
                bi_max=data.get("bi_max"),
                pb_min=data.get("pb_min"),
                pb_max=data.get("pb_max"),
                sn_min=data.get("sn_min"),
                sn_max=data.get("sn_max"),
                others_each_min=data.get("others_each_min"),
                others_each_max=data.get("others_each_max"),
                others_total_min=data.get("others_total_min"),
                others_total_max=data.get("others_total_max"),
                al_min=data.get("al_min"),
                al_max=data.get("al_max"),
                remark=data.get("remark"),
                created_by=request.user,
                created_at=timezone.now(),
                updated_by=None,
                updated_at=None,
                deleted=False,
            )

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Alloy",
                description=f"Created Alloy '{alloy.alloy_code}'",
                request=request,
                payload=clean_payload(request.data),
            )

            return Response(
                {
                    "success": True,
                    "data": {"id": alloy.id, "alloy_code": alloy.alloy_code},
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return custom_exception(e)

    def update(self, request, *args, **kwargs):
        try:
            alloy_id = kwargs.get("pk")
            data = request.data

            try:
                alloy = Alloy.objects.get(id=alloy_id, deleted=False)
            except Alloy.DoesNotExist:
                return Response(
                    {"success": False, "message": "Alloy not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            alloy_code = data.get("alloy_code", alloy.alloy_code)
            standard_id = data.get("standard", alloy.standard_id)

            color_code = data.get("color_code", alloy.color_code)
            if color_code == "":
                color_code = None

            duplicate_query = Alloy.objects.filter(
                alloy_code__iexact=alloy_code,
                standard_id=standard_id,
                deleted=False,
            ).exclude(id=alloy.id)

            if color_code is None:
                duplicate_query = duplicate_query.filter(color_code__isnull=True)
            else:
                duplicate_query = duplicate_query.filter(color_code=color_code)

            if duplicate_query.exists():
                return Response(
                    {"success": False, "message": "This alloy already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for key in data:
                if data[key] == "":
                    data[key] = None

            if "standard" in data:
                data["standard_id"] = data["standard"]

            optional_fields = [
                "color_code",
                "si_min",
                "si_max",
                "mg_min",
                "mg_max",
                "fe_min",
                "fe_max",
                "mn_min",
                "mn_max",
                "cu_min",
                "cu_max",
                "zn_min",
                "zn_max",
                "cr_min",
                "cr_max",
                "ti_min",
                "ti_max",
                "bi_min",
                "bi_max",
                "pb_min",
                "pb_max",
                "sn_min",
                "sn_max",
                "others_each_min",
                "others_each_max",
                "others_total_min",
                "others_total_max",
                "remark",
            ]
            for f in optional_fields:
                if f not in data:
                    data[f] = None

            min_max_pairs = [
                ("si_min", "si_max", "Si"),
                ("mg_min", "mg_max", "Mg"),
                ("fe_min", "fe_max", "Fe"),
                ("mn_min", "mn_max", "Mn"),
                ("cu_min", "cu_max", "Cu"),
                ("zn_min", "zn_max", "Zn"),
                ("cr_min", "cr_max", "Cr"),
                ("ti_min", "ti_max", "Ti"),
                ("bi_min", "bi_max", "Bi"),
                ("pb_min", "pb_max", "Pb"),
                ("sn_min", "sn_max", "Sn"),
                ("others_each_min", "others_each_max", "Others Each"),
                ("others_total_min", "others_total_max", "Others Total"),
            ]

            for min_field, max_field, field_name in min_max_pairs:
                min_val = data.get(min_field)
                max_val = data.get(max_field)
                if min_val is not None and max_val is not None:
                    try:
                        min_dec = Decimal(str(min_val))
                        max_dec = Decimal(str(max_val))
                        if min_dec > max_dec:
                            return Response(
                                {
                                    "success": False,
                                    "message": f"{field_name} Min cannot be greater than Max.",
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    except (ValueError, TypeError):
                        pass

            payload = {}
            for f in Alloy.AL_COMPONENT_MIN_FIELDS + Alloy.AL_COMPONENT_MAX_FIELDS:
                payload[f] = data.get(f)

            def _has_any(fields) -> bool:
                for f in fields:
                    v = payload.get(f)
                    if v is None:
                        continue
                    if isinstance(v, str) and v.strip() == "":
                        continue
                    return True
                return False

            has_min_values = _has_any(Alloy.AL_COMPONENT_MIN_FIELDS)
            has_max_values = _has_any(Alloy.AL_COMPONENT_MAX_FIELDS)

            if has_min_values:
                sum_min = sum(
                    (Decimal(str(payload.get(f) or 0)))
                    for f in Alloy.AL_COMPONENT_MIN_FIELDS
                )
                if sum_min > Decimal("100"):
                    return Response(
                        {
                            "success": False,
                            "message": "Sum of all Min fields cannot exceed 100.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if has_max_values:
                sum_max = sum(
                    (Decimal(str(payload.get(f) or 0)))
                    for f in Alloy.AL_COMPONENT_MAX_FIELDS
                )
                if sum_max > Decimal("100"):
                    return Response(
                        {
                            "success": False,
                            "message": "Sum of all Max fields cannot exceed 100.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            for field in [
                "alloy_code",
                "color_code",
                "standard_id",
                "si_min",
                "si_max",
                "mg_min",
                "mg_max",
                "fe_min",
                "fe_max",
                "mn_min",
                "mn_max",
                "cu_min",
                "cu_max",
                "zn_min",
                "zn_max",
                "cr_min",
                "cr_max",
                "ti_min",
                "ti_max",
                "bi_min",
                "bi_max",
                "pb_min",
                "pb_max",
                "sn_min",
                "sn_max",
                "others_each_min",
                "others_each_max",
                "others_total_min",
                "others_total_max",
                "al_min",
                "al_max",
                "remark",
            ]:
                if field in data:
                    setattr(alloy, field, data[field])

            alloy.updated_by = request.user
            alloy.updated_at = timezone.now()
            alloy.save()

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Alloy",
                description=f"Updated Alloy '{alloy.alloy_code}'",
                request=request,
                payload=clean_payload(request.data),
            )

            return Response(
                {
                    "success": True,
                    "data": {"id": alloy.id},
                    "message": "Alloy updated successfully",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            can_delete, error_message = self._can_delete_alloy(instance)
            if not can_delete:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.queryset.filter(pk=instance.pk).update(
                deleted=True,
                deleted_by=request.user,
                deleted_at=timezone.now(),
            )

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="ARCHIVE",
                module_name="Alloy",
                description=f"Archived Alloy '{getattr(instance, 'alloy_code', '')}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "message": "Record Archived"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return custom_exception(e)

    def _can_delete_alloy(self, alloy):
        from bundle_inward.models import ExcessStock
        from die.models import ConversionRate
        from die_quotation.models import DieQuotationDetails
        from inquiry_quotation.models import InquiryQuotationDetail
        from inquiry_salesorder.models import InquirySalesOrderDetail
        from production.models import Production
        from proforma.models import ProformaDetails
        from quotation.models import QuotationDetail
        from workorder.models import WorkOrderDetail

        if WorkOrderDetail.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Work Order records.",
            )

        if QuotationDetail.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Quotation records.",
            )

        if ProformaDetails.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Proforma records.",
            )

        if InquirySalesOrderDetail.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Inquiry Sales Order records.",
            )

        if InquiryQuotationDetail.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Inquiry Quotation records.",
            )

        if DieQuotationDetails.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Die Quotation records.",
            )

        if Production.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Production records.",
            )

        if ExcessStock.objects.filter(alloy=alloy, deleted=False).exists():
            return (
                False,
                "Cannot archive Alloy. It is referenced by active Excess Stock records.",
            )

        # if ConversionRate.objects.filter(alloy=alloy, deleted=False).exists():
        #     return (
        #         False,
        #         "Cannot archive Alloy. It is referenced by active Conversion Rate records.",
        #     )

        return True, None

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = Alloy.objects.filter(deleted=False)

        filter_param = request.query_params.get("filter")
        if filter_param:
            queryset = (
                queryset.filter(alloy_code__icontains=filter_param),
                queryset.filter(color_code__icontains=filter_param)
            )

        serializer = AlloyDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def _validate_bulk_request(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return None, Response(
                {"success": False, "message": "ids field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(ids, list):
            return None, Response(
                {"success": False, "message": "ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(ids) == 0:
            return None, Response(
                {"success": False, "message": "ids list cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return ids, None

    def _archive_alloys(self, alloy_ids, user):
        alloys = Alloy.objects.filter(id__in=alloy_ids, deleted=False)

        if not alloys.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active alloys found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        referenced_alloys = []
        for alloy in alloys:
            can_delete, error_message = self._can_delete_alloy(alloy)
            if not can_delete:
                referenced_alloys.append(f"{alloy.alloy_code} ({alloy.standard_name.name if alloy.standard_name else 'No Standard'})")

        if referenced_alloys:
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": f"Cannot archive alloys referenced by active records: {', '.join(referenced_alloys)}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        archived_names = list(alloys.values_list("alloy_code", flat=True))
        updated_count = alloys.update(
            deleted=True,
            deleted_by=user,
            deleted_at=timezone.now(),
            updated_by=user,
            updated_at=timezone.now(),
        )

        return updated_count, archived_names, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        try:
            alloy_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_names, error_response = self._archive_alloys(
                    alloy_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Alloy",
                    description=f"Archived {updated_count} alloy(s): {', '.join(archived_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} alloy(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_alloys(self, alloy_ids, user):
        alloys = Alloy.objects.filter(id__in=alloy_ids, deleted=True)

        if not alloys.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived alloys found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_names = list(alloys.values_list("alloy_code", flat=True))
        updated_count = alloys.update(
            deleted=False,
            deleted_by=None,
            deleted_at=None,
        )

        return updated_count, restored_names, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        try:
            alloy_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_names, error_response = self._restore_alloys(
                    alloy_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Alloy",
                    description=f"Restored {updated_count} alloy(s): {', '.join(restored_names)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = Alloy.objects.filter(id__in=alloy_ids)
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} alloy(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        try:
            queryset = (
                Alloy.objects.filter(deleted=True)
                .select_related("created_by", "deleted_by")
                .order_by("-deleted_at")
            )

            queryset = self.filter_queryset(queryset)

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

    @action(detail=True, methods=["get"], url_path="archived")
    def get_archived(self, request, pk=None):
        try:
            instance = (
                Alloy.objects.filter(id=pk, deleted=True)
                .select_related("created_by", "deleted_by")
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived alloy not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)

    def _parse_dry_run_param(self, dry_run_param):
        if isinstance(dry_run_param, str):
            return dry_run_param.lower() in ("true", "1", "yes")
        return bool(dry_run_param)

    def _format_import_log(self, log):
        return {
            "id": str(log.id),
            "file_name": log.file_name,
            "status": log.status,
            "total_rows": log.total_rows,
            "success_count": log.success_count,
            "error_count": log.error_count,
            "success_rate": log.success_rate,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "created_by": log.created_by.id if log.created_by else None,
        }

    def _log_import_start(self, file, dry_run, user_id):
        try:
            logger.info(
                "Bulk import started",
                extra={
                    "module_name": "Alloy",
                    "file_name": getattr(file, "name", "unknown"),
                    "file_size": getattr(file, "size", 0),
                    "dry_run": dry_run,
                    "user_id": user_id,
                },
            )
        except Exception as e:
            logger.warning(f"Error logging import start: {str(e)}")

    def _log_import_complete(self, result):
        logger.info(
            "Bulk import completed",
            extra={
                "module_name": "Alloy",
                "total_rows": (
                    result.get("data", {}).get("total_records", 0)
                    if isinstance(result, dict)
                    else 0
                ),
                "success_count": (
                    result.get("data", {}).get("success_count", 0)
                    if isinstance(result, dict)
                    else 0
                ),
                "error_count": (
                    result.get("data", {}).get("error_count", 0)
                    if isinstance(result, dict)
                    else 0
                ),
            },
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            from imports.services.alloy_importer import AlloyImporter

            importer = AlloyImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            self._log_import_complete(result)

            is_success = (
                bool(result.get("success", False))
                if isinstance(result, dict)
                else False
            )
            if not is_success:
                return self._format_import_response(
                    result,
                    is_success=False,
                    error_message=(
                        result.get("message")
                        if isinstance(result, dict)
                        else "Import failed"
                    ),
                    error_status_code=status.HTTP_400_BAD_REQUEST,
                )

            return self._format_import_response(result, is_success=True)
        except Exception as e:
            return self._handle_import_exception(e, request)

    def _validate_import_file(self, request):
        if "file" not in request.FILES:
            return None, Response(
                {"success": False, "message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return request.FILES["file"], None

    def _format_import_response(
        self,
        result,
        is_success,
        error_message=None,
        error_status_code=status.HTTP_400_BAD_REQUEST,
    ):
        if not isinstance(result, dict):
            return Response(
                {"success": False, "message": error_message or "Import failed"},
                status=error_status_code,
            )

        if is_success:
            return Response(result, status=status.HTTP_200_OK)

        return Response(result, status=error_status_code)

    def _handle_import_exception(self, e, request):
        logger.error(
            "Bulk import error",
            extra={
                "module_name": "Alloy",
                "error": str(e),
                "user_id": request.user.id if request.user else None,
            },
            exc_info=True,
        )
        return Response(
            {
                "success": False,
                "message": f"Import failed: {str(e)}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _format_error_row(self, row):
        return {
            "row_number": row.row_number,
            "error_type": row.error_type,
            "field_name": row.field_name,
            "error_message": row.error_message,
            "raw_data": row.raw_data,
        }

    def _build_error_summary(self, error_rows):
        summary = {
            "total_errors": error_rows.count(),
            "error_types": {},
        }
        for row in error_rows:
            error_type = row.error_type
            summary["error_types"][error_type] = (
                summary["error_types"].get(error_type, 0) + 1
            )
        return summary

    def _generate_csv_response(self, error_rows, import_log_id):
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(
            ["Row Number", "Error Type", "Field Name", "Error Message", "Raw Data"]
        )

        for row in error_rows:
            writer.writerow(
                [
                    row.row_number,
                    row.error_type,
                    row.field_name or "",
                    row.error_message,
                    str(row.raw_data) if row.raw_data else "",
                ]
            )

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="alloy_import_errors_{import_log_id}.csv"'
        )
        return response


class AlloyArchiveViewSet(ArchiveMixin):
    queryset = (
        Alloy.objects.filter(deleted=True)
        .select_related("created_by", "deleted_by")
        .order_by("-deleted_at")
    )
    serializer_class = AlloySerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = [
        "alloy_code",
        "color_code",
        "created_by__first_name",
        "created_by__last_name",
    ]
    ordering_fields = [
        "alloy_code",
        "color_code",
        "created_at",
        "updated_at",
        "deleted_at",
    ]
    ordering = ["-deleted_at"]
    http_method_names = ["get"]

    def get_queryset(self):
        """Filter archived alloys"""
        queryset = super().get_queryset()
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived alloys with pagination"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
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
        """Retrieve a single archived alloy"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)
