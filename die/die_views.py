import json
import logging
from django.db.models import Q
from django.forms import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin, FinancialYearModel

from imports.models import ImportErrorRow, ImportLog
from imports.services.section_ballon_dimension_importer import (
    SectionBallonDimensionsImporter,
)
from imports.services.section_importer import DieImporter
from die.master_serializers import DieListSerializers
from die.models import Die, DieTool, SectionBallonDimensions
from die.serializers import DieSerializers, QuickDieSerializer
from user.models import User
from utils.aws_file_upload import delete_uploaded_die_file
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

from .serializers import SectionBallonDimensionsSerializer

logger = logging.getLogger("file")


class DieViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Die.objects.select_related(
            "die_group",
            "die_category",
            "die_sub_category",
            "created_by",
            "updated_by",
            "deleted_by",
        ).all().order_by("-created_at")
    )
    serializer_class = DieSerializers
    list_serializer_class = DieListSerializers
    fy_filtering_enabled = False

    search_fields = BaseModelViewSet.serching_fields + [
        "die_number",
        "dimension1",
        "dimension2",
        "dimension3",
        "dimension4",
        "min_wt_kg_p_mt",
        "wt_kg_p_mt",
        "max_wt_kg_p_mt",
        "die_group__name",
        "die_category__name",
        "die_sub_category__name",
        "die_diagram",
        "die_detail_diagram",
        "customer_approved_diagram",
        "autocad_drawing",
        "die_manufacturing",
        "die_sop",
        "customer_reference_number",
        "die_type",
        "remarks",
        "front_end_process_loss_mm",
        "back_end_process_loss_mm",
        "stretching_head_loss_mm",
        "stretching_tail_loss_mm",
        "total_process_loss_mm",
        "total_process_loss_meter",
        "total_process_loss_kg",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = search_fields

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        die_group = params.get("die_group") or params.get("groupId")
        if die_group:
            queryset = queryset.filter(die_group_id=die_group)

        die_category = params.get("die_category")
        if die_category:
            queryset = queryset.filter(die_category_id=die_category)

        die_sub_category = params.get("die_sub_category")
        if die_sub_category:
            queryset = queryset.filter(die_sub_category_id=die_sub_category)

        die_type = params.get("die_type")
        if die_type:
            queryset = queryset.filter(die_type__iexact=die_type)

        return queryset

    @action(detail=False, methods=["POST"], url_path="quick-section-add")
    def quick_die_add(self, request, *args, **kwargs):
        serializer = QuickDieSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        die = serializer.save(created_by=request.user)

        log_user_activity(
            user=request.user,
            action="CREATE",
            module_name="Die",
            description=f"Quick created Die '{die.die_number}'",
            request=request,
            payload=clean_payload(request.data),
        )
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def create(self, request, *args, **kwargs):
        data = json.loads(request.data["form_data"])
        data["created_at"] = timezone.now()
        data["updated_at"] = None

        file_fields = {
            "die_diagram": request.FILES.get("die_diagram"),
            "die_detail_diagram": request.FILES.get("die_detail_diagram"),
            "customer_approved_diagram": request.FILES.get("customer_approved_diagram"),
            "autocad_drawing": request.FILES.get("autocad_drawing"),
            "die_manufacturing": request.FILES.get("die_manufacturing"),
            "die_sop": request.FILES.get("die_sop"),
        }

        uploaded_files = {
            key: file for key, file in file_fields.items() if file is not None
        }

        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            die = serializer.save(created_by=request.user)

            try:
                die.upload_doc(uploaded_files)
            except ValidationError as e:
                return Response(
                    {"success": False, "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            errors = serializer.errors
            if "non_field_errors" in errors:
                error_message = errors["non_field_errors"][0]
            else:
                error_message = serializer.errors

            return Response(
                {"success": False, "message": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        data = json.loads(request.data["form_data"])
        data["updated_at"] = timezone.now()

        die_diagram = request.FILES.get("die_diagram")
        die_detail_diagram = request.FILES.get("die_detail_diagram")
        customer_approved_diagram = request.FILES.get("customer_approved_diagram")
        autocad_drawing = request.FILES.get("autocad_drawing")
        die_manufacturing = request.FILES.get("die_manufacturing")
        die_sop = request.FILES.get("die_sop")

        doc_dict = {
            "die_diagram": die_diagram,
            "die_detail_diagram": die_detail_diagram,
            "customer_approved_diagram": customer_approved_diagram,
            "autocad_drawing": autocad_drawing,
            "die_manufacturing": die_manufacturing,
            "die_sop": die_sop,
        }

        try:
            instance = self.get_object()
            serializer = self.serializer_class(
                instance, data=data, partial=True, context={"request": request}
            )

            if serializer.is_valid():
                die = serializer.save(
                    updated_by=request.user, updated_at=timezone.now()
                )

                try:
                    die.upload_doc(doc_dict)
                except ValidationError as e:
                    return Response(
                        {"success": False, "message": e.args[0]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                logger.info("Record updated successfully.")

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )

            else:
                logger.error(f"Error in updating record : {serializer.errors}")
                errors = serializer.errors
                if "non_field_errors" in errors:
                    error_message = errors["non_field_errors"][0]
                else:
                    error_message = serializer.errors

                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return custom_exception(e)

    @action(detail=True, methods=["patch"], url_path="upload-file")
    def upload_file(self, request, pk=None):
        try:
            die = Die.objects.get(id=pk)
        except Die.DoesNotExist:
            return Response(
                {"success": False, "message": "Die not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_fields = [
            "die_diagram",
            "die_detail_diagram",
            "customer_approved_diagram",
            "autocad_drawing",
            "die_manufacturing",
            "die_sop",
        ]

        uploaded_field = None
        uploaded_file = None

        for field in file_fields:
            if field in request.FILES:
                uploaded_field = field
                uploaded_file = request.FILES[field]
                break

        if not uploaded_field:
            return Response(
                {"success": False, "message": "Please upload exactly one file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            die.upload_doc({uploaded_field: uploaded_file})

            file_url = getattr(die, uploaded_field, None)

            if file_url:
                return Response(
                    {
                        "success": True,
                        "message": f"{uploaded_field} uploaded successfully.",
                        uploaded_field: file_url,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"success": False, "message": "File upload failed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except ValidationError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            queryset = Die.objects.filter(deleted=False).select_related(
                "die_group",
                "die_category",
                "die_sub_category",
                "created_by",
                "updated_by",
            )
            instance = queryset.get(pk=self.kwargs["pk"])
            serializer = self.get_serializer(instance)
            return Response({"success": True, "data": serializer.data})
        except Exception as e:
            return Response(
                {"success": False, "message": f"No Die matches the given ID."},
                status=status.HTTP_204_NO_CONTENT,
            )

    def _parse_dry_run_param(self, dry_run_param):
        """Helper method to parse dry_run parameter"""
        if isinstance(dry_run_param, str):
            return dry_run_param.lower() in ("true", "1", "yes")
        return bool(dry_run_param)

    def _format_import_log(self, log):
        """Helper method to format import log data"""
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
        """Log bulk import start"""
        logger.info(
            "Bulk import started",
            extra={
                "module": "Die",
                "file_name": file.name,
                "file_size": file.size,
                "dry_run": dry_run,
                "user_id": user_id,
            },
        )

    def _log_import_complete(self, result):
        """Log bulk import completion"""
        logger.info(
            "Bulk import completed",
            extra={
                "module_name": "Die",
                "success": result.get("success"),
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    def _handle_import_exception(self, e, request):
        """Handle bulk import exceptions"""
        if isinstance(e, ValueError):
            logger.warning(f"Validation error in bulk import: {str(e)}", exc_info=True)
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(e),
                error_status_code=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.error(
                "Error in bulk import",
                extra={
                    "module_name": "Die",
                    "error": str(e),
                    "user_id": request.user.id,
                },
                exc_info=True,
            )
            return self._format_import_response(
                None,
                is_success=False,
                error_message="Internal server error during import",
                error_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import dies from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            importer = DieImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            self._log_import_complete(result)

            return self._format_import_response(result, is_success=True)
        except Exception as e:
            return self._handle_import_exception(e, request)

    def _validate_import_file(self, request):
        """Validate import file"""
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
        """Format import response to match temper_importer.py"""
        if is_success and result:
            return Response(
                {
                    "success": result.get("success", True),
                    "message": result.get("message", "Import completed successfully"),
                    "data": result.get("data", {}),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": error_message or "Import failed",
                },
                status=error_status_code,
            )

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for Die module"""
        logs = (
            ImportLog.objects.filter(module_name="Die")
            .select_related("created_by")
            .order_by("-started_at")
        )

        queryset = logs
        page = self.paginate_queryset(queryset)

        if page is not None:
            data = [self._format_import_log(log) for log in page]
            return self.get_paginated_response({"success": True, "data": data})

        data = [self._format_import_log(log) for log in queryset]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    def _format_error_row(self, row):
        """Format error row data"""
        return {
            "row_number": row.row_number,
            "error_type": row.error_type,
            "field_name": row.field_name,
            "error_message": row.error_message,
            "raw_data": row.raw_data,
        }

    @action(detail=True, methods=["get"], url_path="import-errors")
    def import_errors(self, request, pk=None):
        """
        Get errors for a specific import log.
        Note: pk here is import_log_id, not die_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Die"
            )
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        error_rows = ImportErrorRow.objects.filter(import_log=import_log).order_by(
            "row_number"
        )

        errors = [self._format_error_row(row) for row in error_rows]
        summary = self._build_error_summary(error_rows)

        return Response(
            {"success": True, "data": {"summary": summary, "errors": errors}},
            status=status.HTTP_200_OK,
        )

    def _build_error_summary(self, error_rows):
        """Build error summary from error rows"""
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

class SectionBalloonDimensionsViewSet(ModelViewSet):
    queryset = SectionBallonDimensions.objects.filter(deleted=False)
    serializer_class = SectionBallonDimensionsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            section_id = request.query_params.get("section_id")

            if section_id:
                queryset = queryset.filter(section_id=section_id)

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        try:
            dimension = self.get_object()
            dimension.deleted = True
            dimension.deleted_by = request.user
            dimension.deleted_at = timezone.now()
            dimension.save()
            return Response(
                {"success": True, "message": "Balloon dimension deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _parse_dry_run_param(self, dry_run_param):
        """Helper method to parse dry_run parameter"""
        if isinstance(dry_run_param, str):
            return dry_run_param.lower() in ("true", "1", "yes")
        return bool(dry_run_param)

    def _format_import_log(self, log):
        """Helper method to format import log data"""
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
        """Log bulk import start"""
        logger.info(
            "Bulk import started",
            extra={
                "module": "SectionBallonDimensions",
                "file_name": file.name,
                "file_size": file.size,
                "dry_run": dry_run,
                "user_id": user_id,
            },
        )

    def _log_import_complete(self, result):
        """Log bulk import completion"""
        logger.info(
            "Bulk import completed",
            extra={
                "module_name": "SectionBallonDimensions",
                "success": result.get("success"),
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    def _handle_import_exception(self, e, request):
        """Handle bulk import exceptions"""
        if isinstance(e, ValueError):
            logger.warning(f"Validation error in bulk import: {str(e)}", exc_info=True)
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(e),
                error_status_code=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.error(
                "Error in bulk import",
                extra={
                    "module_name": "SectionBallonDimensions",
                    "error": str(e),
                    "user_id": request.user.id,
                },
                exc_info=True,
            )
            return self._format_import_response(
                None,
                is_success=False,
                error_message="Internal server error during import",
                error_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import section balloon dimensions from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            importer = SectionBallonDimensionsImporter(
                file, user=request.user, dry_run=dry_run
            )
            result = importer.import_data()
            self._log_import_complete(result)

            return self._format_import_response(result, is_success=True)
        except Exception as e:
            return self._handle_import_exception(e, request)

    def _validate_import_file(self, request):
        """Validate import file"""
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
        """Format import response"""
        if is_success and result:
            return Response(
                {
                    "success": result.get("success", True),
                    "message": result.get("message", "Import completed successfully"),
                    "data": result.get("data", {}),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": error_message or "Import failed",
                },
                status=error_status_code,
            )

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for SectionBallonDimensions module"""
        logs = (
            ImportLog.objects.filter(module_name="SectionBallonDimensions")
            .select_related("created_by")
            .order_by("-started_at")
        )

        queryset = logs
        page = self.paginate_queryset(queryset)

        if page is not None:
            data = [self._format_import_log(log) for log in page]
            return self.get_paginated_response({"success": True, "data": data})

        data = [self._format_import_log(log) for log in queryset]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    def _format_error_row(self, row):
        """Format error row data"""
        return {
            "row_number": row.row_number,
            "error_type": row.error_type,
            "field_name": row.field_name,
            "error_message": row.error_message,
            "raw_data": row.raw_data,
        }

    @action(detail=True, methods=["get"], url_path="import-errors")
    def import_errors(self, request, pk=None):
        """
        Get errors for a specific import log.
        Note: pk here is import_log_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="SectionBallonDimensions"
            )
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        error_rows = ImportErrorRow.objects.filter(import_log=import_log).order_by(
            "row_number"
        )

        errors = [self._format_error_row(row) for row in error_rows]
        summary = self._build_error_summary(error_rows)

        return Response(
            {"success": True, "data": {"summary": summary, "errors": errors}},
            status=status.HTTP_200_OK,
        )

    def _build_error_summary(self, error_rows):
        """Build error summary from error rows"""
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


class DeleteDieUploadedFile(ModelViewSet):
    queryset = Die.objects.all().order_by("-id")
    serializer_class = DieSerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        fields_to_update = {
            "die_diagram": request.data.get("die_diagram"),
            "die_detail_diagram": request.data.get("die_detail_diagram"),
            "customer_approved_diagram": request.data.get("customer_approved_diagram"),
            "autocad_drawing": request.data.get("autocad_drawing"),
            "die_manufacturing": request.data.get("die_manufacturing"),
            "die_sop": request.data.get("die_sop"),
        }
        deleted_fields = []

        for field, provided_url in fields_to_update.items():
            if provided_url is not None:
                file_exists = delete_uploaded_die_file(provided_url)
                if not file_exists:
                    return Response(
                        {"error": f"File for {field} does not exist in S3."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                setattr(instance, field, None)

                instance.save()
                deleted_fields.append(field)

        if not deleted_fields:
            return Response(
                {"error": "No valid fields provided for deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.save()

        return Response(
            {
                "message": "Selected file(s) deleted successfully.",
                "deleted_fields": deleted_fields,
            },
            status=status.HTTP_200_OK,
        )
