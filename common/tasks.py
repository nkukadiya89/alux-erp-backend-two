import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.utils.timezone import now
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from workorder.models import WorkOrderDetail

logger = logging.getLogger(__name__)


@shared_task
def cleanup_outstanding_tokens():
    """
    Clean up outstanding tokens older than 30 days
    """
    thirty_days_ago = datetime.now() - timedelta(days=30)
    OutstandingToken.objects.filter(created_at__lt=thirty_days_ago).delete()


@shared_task
def logout_all_users():
    """
    Blacklist all valid outstanding tokens to force logout.
    """


@shared_task(bind=True, name="common.tasks.bulk_import_item_categories_async")
def bulk_import_item_categories_async(
    self, file_path: str, user_id: int, import_log_id: str, dry_run: bool = False
):
    """
    Async Celery task for bulk importing Item Categories.
    Used for large imports (>1000 rows) to avoid blocking the request thread.

    Args:
        file_path: Path to the uploaded file (temporary storage)
        user_id: ID of the user performing the import
        import_log_id: UUID of the ImportLog record
        dry_run: If True, validate only without saving

    Returns:
        Dictionary with import results
    """
    import os

    from django.contrib.auth import get_user_model
    from django.core.files import File
    from django.core.files.uploadedfile import (
        InMemoryUploadedFile,
        TemporaryUploadedFile,
    )

    from imports.models import ImportLog
    from imports.services.item_category_importer import ItemCategoryImporter

    User = get_user_model()
    logger.info(
        "Starting async bulk import task",
        extra={
            "module_name": "Item Category",
            "task_id": self.request.id,
            "import_log_id": import_log_id,
            "user_id": user_id,
            "file_path": file_path,
        },
    )

    try:
        # Get user and import log
        user = User.objects.get(id=user_id)
        import_log = ImportLog.objects.get(id=import_log_id)

        # Update task status
        import_log.status = "processing"
        import_log.save()

        # Open file and process
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_obj = File(f, name=os.path.basename(file_path))
                importer = ItemCategoryImporter(file_obj, user=user, dry_run=dry_run)
                result = importer.import_data()
        else:
            raise FileNotFoundError(f"Temporary file not found: {file_path}")

        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_error:
            logger.warning(
                "Failed to cleanup temporary file",
                extra={
                    "module_name": "Item Category",
                    "file_path": file_path,
                    "error": str(cleanup_error),
                },
            )

        logger.info(
            "Async bulk import completed",
            extra={
                "module_name": "Item Category",
                "task_id": self.request.id,
                "import_log_id": import_log_id,
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

        return result

    except Exception as e:
        logger.error(
            "Async bulk import failed",
            extra={
                "module_name": "Item Category",
                "task_id": self.request.id,
                "import_log_id": import_log_id,
                "error": str(e),
            },
            exc_info=True,
        )

        # Update import log
        try:
            import_log = ImportLog.objects.get(id=import_log_id)
            import_log.mark_failed(str(e))
        except Exception:
            pass

        # Clean up file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        raise
    tokens = OutstandingToken.objects.filter(blacklistedtoken__isnull=True)
    count = 0
    for token in tokens:
        try:
            BlacklistedToken.objects.create(token=token)
            OutstandingToken.objects.delete(token=token)
            count += 1
        except Exception:
            # Token is probably already blacklisted
            continue
    return f"Logged out {count} users (blacklisted tokens)"


@shared_task
def update_workorderdetail_priority():
    """
    Update WorkOrderDetail priority based on WorkOrder delivery_date
    """
    today = now().date()
    target_date = today + timedelta(days=4)

    # Reset all priority flags first
    # WorkOrderDetail.objects.update(is_priority=False)

    # Update WorkOrderDetails whose WorkOrder delivery_date is within 4 days
    updated_count = WorkOrderDetail.objects.filter(
        workorder__delivery_date__range=(today, target_date)
    ).update(is_priority=True)

    return f"Updated {updated_count} WorkOrderDetails as priority"
