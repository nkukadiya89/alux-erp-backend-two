import os
import uuid
import logging

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from imports.models import ImportLog
from imports.utils import validate_file_extension, get_file_type

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "section_imports")
UPLOAD_DIR_BALLOON = os.path.join(settings.MEDIA_ROOT, "balloon_imports")


class SectionAsyncImportAPIView(APIView):
    """
    POST  /api/v1/section-import-async/
        Accepts a file upload, creates an ImportLog (status=pending),
        queues a Celery background task, and immediately returns the import_log_id.

    GET   /api/v1/section-import-async/?import_log_id=<uuid>
        Returns the current status and result of the import job.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"success": False, "message": "File is required."}, status=400)

        if not validate_file_extension(file.name, ALLOWED_EXTENSIONS):
            return Response(
                {"success": False, "message": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
                status=400,
            )

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(file.name)[1]
        saved_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, saved_name)

        with open(file_path, "wb") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        file_type = get_file_type(file.name) or "unknown"
        import_log = ImportLog.objects.create(
            module_name="Die",
            file_name=file.name,
            file_type=file_type,
            status="pending",
            created_by=request.user,
        )

        from imports.tasks import run_section_import
        run_section_import.delay(str(import_log.id), file_path, request.user.id)

        return Response(
            {
                "success": True,
                "message": "Import queued successfully. Use the import_log_id to track progress.",
                "data": {"import_log_id": str(import_log.id), "status": "pending"},
            },
            status=202,
        )

    def get(self, request):
        import_log_id = request.query_params.get("import_log_id")
        if not import_log_id:
            return Response({"success": False, "message": "import_log_id is required."}, status=400)

        try:
            log = ImportLog.objects.get(id=import_log_id)
        except ImportLog.DoesNotExist:
            return Response({"success": False, "message": "Import log not found."}, status=404)

        data = {
            "import_log_id": str(log.id),
            "status": log.status,
            "module_name": log.module_name,
            "file_name": log.file_name,
            "total_rows": log.total_rows,
            "success_count": log.success_count,
            "error_count": log.error_count,
            "started_at": log.started_at,
            "completed_at": log.completed_at,
        }

        if log.status == "failed" and log.error_summary:
            data["error_summary"] = log.error_summary

        return Response({"success": True, "data": data})


UPLOAD_DIR_DIETOOL = os.path.join(settings.MEDIA_ROOT, "dietool_imports")


class DieToolAsyncImportAPIView(APIView):
    """
    POST  /api/v1/dietool-import-async/
        Accepts a file upload, creates an ImportLog (status=pending),
        queues a Celery background task, and immediately returns the import_log_id.

    GET   /api/v1/dietool-import-async/?import_log_id=<uuid>
        Returns the current status and result of the import job.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"success": False, "message": "File is required."}, status=400)

        if not validate_file_extension(file.name, ALLOWED_EXTENSIONS):
            return Response(
                {"success": False, "message": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
                status=400,
            )

        os.makedirs(UPLOAD_DIR_DIETOOL, exist_ok=True)
        ext = os.path.splitext(file.name)[1]
        saved_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR_DIETOOL, saved_name)

        with open(file_path, "wb") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        file_type = get_file_type(file.name) or "unknown"
        import_log = ImportLog.objects.create(
            module_name="DieTool",
            file_name=file.name,
            file_type=file_type,
            status="pending",
            created_by=request.user,
        )

        from imports.tasks import run_dietool_import
        run_dietool_import.delay(str(import_log.id), file_path, request.user.id)

        return Response(
            {
                "success": True,
                "message": "Import queued successfully. Use the import_log_id to track progress.",
                "data": {"import_log_id": str(import_log.id), "status": "pending"},
            },
            status=202,
        )

    def get(self, request):
        import_log_id = request.query_params.get("import_log_id")
        if not import_log_id:
            return Response({"success": False, "message": "import_log_id is required."}, status=400)

        try:
            log = ImportLog.objects.get(id=import_log_id)
        except ImportLog.DoesNotExist:
            return Response({"success": False, "message": "Import log not found."}, status=404)

        from imports.models import ImportErrorRow
        from itertools import groupby

        error_rows = (
            ImportErrorRow.objects
            .filter(import_log=log)
            .values("row_number", "field_name", "error_message")
            .order_by("row_number")
        )

        # Group errors by row_number
        errors = []
        for row_number, group in groupby(error_rows, key=lambda x: x["row_number"]):
            errors.append({
                "row": row_number - 1,
                "errors": [
                    f"{e['field_name']}: {e['error_message']}" if e["field_name"] else e["error_message"]
                    for e in group
                ],
            })

        # Fall back to error_summary if ImportErrorRow table has no records yet
        if not errors and log.error_summary:
            errors = (log.error_summary or {}).get("row_errors", [])

        data = {
            "import_log_id": str(log.id),
            "status": log.status,
            "module_name": log.module_name,
            "file_name": log.file_name,
            "total_rows": log.total_rows,
            "success_count": log.success_count,
            "error_count": log.error_count,
            "started_at": log.started_at,
            "completed_at": log.completed_at,
            "errors": errors,
        }

        return Response({"success": True, "data": data})


class BalloonDimensionAsyncImportAPIView(APIView):
    """
    POST  /api/v1/balloon-dimension-import-async/
        Accepts a file upload, creates an ImportLog (status=pending),
        queues a Celery background task, and immediately returns the import_log_id.

    GET   /api/v1/balloon-dimension-import-async/?import_log_id=<uuid>
        Returns the current status and result of the import job.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"success": False, "message": "File is required."}, status=400)

        if not validate_file_extension(file.name, ALLOWED_EXTENSIONS):
            return Response(
                {"success": False, "message": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
                status=400,
            )

        os.makedirs(UPLOAD_DIR_BALLOON, exist_ok=True)
        ext = os.path.splitext(file.name)[1]
        saved_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR_BALLOON, saved_name)

        with open(file_path, "wb") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        file_type = get_file_type(file.name) or "unknown"
        import_log = ImportLog.objects.create(
            module_name="SectionBallonDimensions",
            file_name=file.name,
            file_type=file_type,
            status="pending",
            created_by=request.user,
        )

        from imports.tasks import run_balloon_dimension_import
        run_balloon_dimension_import.delay(str(import_log.id), file_path, request.user.id)

        return Response(
            {
                "success": True,
                "message": "Import queued successfully. Use the import_log_id to track progress.",
                "data": {"import_log_id": str(import_log.id), "status": "pending"},
            },
            status=202,
        )

    def get(self, request):
        import_log_id = request.query_params.get("import_log_id")
        if not import_log_id:
            return Response({"success": False, "message": "import_log_id is required."}, status=400)

        try:
            log = ImportLog.objects.get(id=import_log_id)
        except ImportLog.DoesNotExist:
            return Response({"success": False, "message": "Import log not found."}, status=404)

        from imports.models import ImportErrorRow
        from itertools import groupby

        error_rows = list(
            ImportErrorRow.objects
            .filter(import_log=log)
            .values("row_number", "field_name", "error_message", "error_type")
            .order_by("row_number")
        )

        errors = []
        for row_number, group in groupby(error_rows, key=lambda x: x["row_number"]):
            row_errors = [
                {
                    "field": e["field_name"] or "general",
                    "error_type": e["error_type"],
                    "reason": e["error_message"],
                }
                for e in group
            ]
            errors.append({
                "row_number": row_number,
                "error_count": len(row_errors),
                "details": row_errors,
            })

        if not errors and log.error_summary:
            errors = (log.error_summary or {}).get("row_errors", [])

        data = {
            "import_log_id": str(log.id),
            "status": log.status,
            "module_name": log.module_name,
            "file_name": log.file_name,
            "total_rows": log.total_rows,
            "success_count": log.success_count,
            "error_count": log.error_count,
            "started_at": log.started_at,
            "completed_at": log.completed_at,
            "error_summary": errors,
        }

        return Response({"success": True, "data": data})
