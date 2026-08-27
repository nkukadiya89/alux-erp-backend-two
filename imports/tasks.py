import logging
import os

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.files import File

from imports.models import ImportLog

logger = logging.getLogger(__name__)

User = get_user_model()


def _cleanup(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Could not delete temp file {file_path}: {e}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_section_import(self, import_log_id: str, file_path: str, user_id: int):
    """
    Background Celery task to import Section (Die) data from a saved file.
    Updates ImportLog status throughout: pending → processing → completed/failed.
    """
    try:
        import_log = ImportLog.objects.get(id=import_log_id)
    except ImportLog.DoesNotExist:
        logger.error(f"ImportLog {import_log_id} not found")
        return

    try:
        import_log.status = "processing"
        import_log.save(update_fields=["status"])

        user = User.objects.filter(id=user_id).first()

        from imports.services.section_importer import DieImporter

        with open(file_path, "rb") as f:
            django_file = File(f, name=os.path.basename(file_path))
            importer = DieImporter(file=django_file, user=user, dry_run=False)
            importer.import_log = import_log
            result = importer._run_import()

        import_log.refresh_from_db()
        logger.info(
            f"Section import {import_log_id} finished: "
            f"inserted={result.get('data', {}).get('inserted')}, "
            f"updated={result.get('data', {}).get('updated')}, "
            f"failed={result.get('data', {}).get('failed')}"
        )

    except Exception as exc:
        logger.error(f"Section import task {import_log_id} failed: {exc}", exc_info=True)
        try:
            import_log.mark_failed(str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc)

    finally:
        _cleanup(file_path)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_balloon_dimension_import(self, import_log_id: str, file_path: str, user_id: int):
    """
    Background Celery task to import SectionBallonDimensions data from a saved file.
    """
    try:
        import_log = ImportLog.objects.get(id=import_log_id)
    except ImportLog.DoesNotExist:
        logger.error(f"ImportLog {import_log_id} not found")
        return

    try:
        import_log.status = "processing"
        import_log.save(update_fields=["status"])

        user = User.objects.filter(id=user_id).first()

        from imports.services.section_ballon_dimension_importer import SectionBallonDimensionsImporter

        with open(file_path, "rb") as f:
            django_file = File(f, name=os.path.basename(file_path))
            importer = SectionBallonDimensionsImporter(file=django_file, user=user, dry_run=False)
            importer.import_log = import_log
            result = importer._run_import()

        import_log.refresh_from_db()
        logger.info(
            f"Balloon dimension import {import_log_id} finished: "
            f"inserted={result.get('data', {}).get('inserted')}, "
            f"updated={result.get('data', {}).get('updated')}, "
            f"failed={result.get('data', {}).get('failed')}"
        )

    except Exception as exc:
        logger.error(f"Balloon dimension import task {import_log_id} failed: {exc}", exc_info=True)
        try:
            import_log.mark_failed(str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc)

    finally:
        _cleanup(file_path)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_dietool_import(self, import_log_id: str, file_path: str, user_id: int):
    """
    Background Celery task to import DieTool data from a saved file.
    """
    try:
        import_log = ImportLog.objects.get(id=import_log_id)
    except ImportLog.DoesNotExist:
        logger.error(f"ImportLog {import_log_id} not found")
        return

    try:
        import_log.status = "processing"
        import_log.save(update_fields=["status"])

        user = User.objects.filter(id=user_id).first()

        from imports.services.dietool_importer import DieToolImporter

        with open(file_path, "rb") as f:
            django_file = File(f, name=os.path.basename(file_path))
            importer = DieToolImporter(file=django_file, user=user, dry_run=False)
            importer.import_log = import_log
            result = importer._run_import()

        row_errors = importer.row_errors or []
        logger.info(
            f"DieTool import {import_log_id} finished: "
            f"inserted={result.get('data', {}).get('inserted')}, "
            f"updated={result.get('data', {}).get('updated')}, "
            f"failed={result.get('data', {}).get('failed')}, "
            f"row_errors_count={len(row_errors)}"
        )

        if row_errors:
            import_log.refresh_from_db()
            import_log.error_summary = {
                "row_errors": [
                    {
                        "row": e.get("row_number"),
                        "errors": [
                            f"{err.get('field', 'unknown')}: {err.get('message', '')}"
                            + (f" (value: {err['value']})" if err.get("value") else "")
                            for err in (e.get("errors") or [])
                        ],
                    }
                    for e in row_errors
                ]
            }
            import_log.save(update_fields=["error_summary"])

    except Exception as exc:
        logger.error(f"DieTool import task {import_log_id} failed: {exc}", exc_info=True)
        try:
            import_log.mark_failed(str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc)

    finally:
        _cleanup(file_path)
