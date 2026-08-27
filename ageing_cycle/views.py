import csv
import logging
from io import StringIO
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from ageing_cycle.models import AgingCycle
from ageing_cycle.serializers import AgingCycleSerializer, AgingCycleListSerializer
from common.models import ArchiveMixin
from common.views import BaseModelViewSet
from imports.models import ImportErrorRow, ImportLog
from django.db.models import Prefetch
from utils.log_activity import clean_payload, log_user_activity

logger = logging.getLogger(__name__)

class AgingCycleViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = AgingCycle.objects.select_related("alloy", "temper").all()
    serializer_class = AgingCycleSerializer
    list_serializer_class = AgingCycleListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        alloy_id = self.request.query_params.get("alloy_id")
        temper_id = self.request.query_params.get("temper_id")

        if alloy_id:
            queryset = queryset.filter(alloy_id=alloy_id)

        if temper_id:
            queryset = queryset.filter(temper_id=temper_id)

        return queryset

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
            """Format import response with row-level error details"""
            if is_success and result:
                row_errors = []
    
                if result.get("import_log_id"):
                    try:
                        from imports.models import ImportErrorRow
    
                        error_rows = ImportErrorRow.objects.filter(
                            import_log_id=result.get("import_log_id")
                        ).order_by("row_number", "id")
    
                        errors_by_row = {}
                        for error_row in error_rows:
                            row_num = error_row.row_number
                            if row_num not in errors_by_row:
                                errors_by_row[row_num] = []
                            errors_by_row[row_num].append(
                                {
                                    "field": error_row.field_name,
                                    "error_type": error_row.error_type,
                                    "message": error_row.error_message,
                                }
                            )
    
                        for row_num in sorted(errors_by_row.keys()):
                            row_errors.append(
                                {
                                    "row_number": row_num,
                                    "errors": errors_by_row[row_num],
                                    "error_count": len(errors_by_row[row_num]),
                                }
                            )
                    except Exception as e:
                        logger.warning(f"Error fetching import errors: {str(e)}")
    
                response_data = {
                    "import_log_id": str(result.get("import_log_id", "")),
                    "total_rows": result.get("total_rows", 0),
                    "inserted": result.get("inserted", 0),
                    "updated": result.get("updated", 0),
                    "skipped": result.get("skipped", 0),
                    "success_count": result.get("success_count", 0),
                    "error_count": result.get("error_count", 0),
                    "dry_run": result.get("dry_run", False),
                }
    
                if row_errors:
                    response_data["row_errors"] = row_errors[:50]
                    if len(row_errors) > 50:
                        response_data["row_errors_truncated"] = True
                        response_data["total_error_rows"] = len(row_errors)
    
                return Response(
                    {
                        "success": True,
                        "message": result.get("message", "Import completed successfully"),
                        "data": response_data,
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
            
    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
           """Bulk import Ageing Cycle from Excel/CSV file"""
           file, error_response = self._validate_import_file(request)
           if error_response:
               return error_response
   
           dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
   
           logger.info(
               "Bulk import started",
               extra={
                   "module_name": "Ageing Cycle",
                   "file_name": file.name if hasattr(file, "name") else "unknown",
                   "file_size": file.size if hasattr(file, "size") else 0,
                   "dry_run": dry_run,
                   "user_id": request.user.id,
               },
           )
   
           try:
               if hasattr(file, "seek"):
                   file.seek(0)
   
               from imports.services.ageing_cycle_importer import AgeingCycleImporter
   
               importer = AgeingCycleImporter(file, user=request.user, dry_run=dry_run)
               result = importer.import_data()
   
               logger.info(
                   "Bulk import completed",
                   extra={
                       "module_name": "Ageing Cycle",
                       "success": result.get("success"),
                       "total_rows": result.get("total_rows", 0),
                       "success_count": result.get("success_count", 0),
                       "error_count": result.get("error_count", 0),
                   },
               )
   
               return self._format_import_response(result, is_success=True)
           except ValueError as e:
               logger.warning(
                   f"Validation error in bulk import: {str(e)}",
                   extra={
                       "module_name": "Ageing Cycle",
                       "user_id": request.user.id,
                   },
                   exc_info=True,
               )
               return self._format_import_response(
                   None,
                   is_success=False,
                   error_message=str(e),
                   error_status_code=status.HTTP_400_BAD_REQUEST,
               )
           except Exception as e:
               logger.error(
                   "Error in bulk import",
                   extra={
                       "module_name": "Ageing Cycle",
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
   