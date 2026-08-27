import os
from typing import Dict, List

from ..models import ImportErrorRow, ImportLog
from ..parsers.csv_parser import CSVParser
from ..parsers.excel_parser import ExcelParser
from ..services.import_factory import ImportFactory


class LegacyImportService:
    """Service to perform legacy-style bulk import processing per model.

    Uses the model-specific Importer (from ImportFactory) for normalize/validate
    and performs create/update operations to produce compat-style response.
    """

    def process_file(
        self, model_name: str, file_path: str, user, import_job_id: int
    ) -> Dict:
        importer = ImportFactory.get_importer(model_name, import_job_id)

        if file_path.lower().endswith((".xlsx", ".xls")):
            parser = ExcelParser(file_path)
        else:
            parser = CSVParser(file_path)

        rows = parser.parse()

        total = len(rows)
        inserted = 0
        updated = 0
        skipped = 0
        failed = 0
        errors_list: List[str] = []

        model_cls = importer.model_class
        unique_field = getattr(importer, "unique_field", None)

        if hasattr(importer, "process_rows"):
            result = importer.process_rows(rows, user)

            self._create_import_log(model_name, user, len(rows), result, importer)

            return result

        for idx, row in enumerate(rows, start=2):
            try:
                normalized = importer.normalize(row)

                unique_val = None
                if unique_field:
                    unique_val = normalized.get(unique_field)

                if unique_field and (
                    unique_val is None
                    or (isinstance(unique_val, str) and unique_val.strip() == "")
                ):
                    skipped += 1
                    errors_list.append(f"Row {idx}: skipped (missing {unique_field})")
                    continue

                try:
                    importer.validate(normalized)
                except Exception as ve:
                    failed += 1
                    errors_list.append(f"Row {idx}: {str(ve)}")
                    continue

                clean_row = {
                    k: v for k, v in normalized.items() if not str(k).startswith("_")
                }
                action = normalized.get("_action", "INSERT")

                if action == "UPDATE" and unique_field and unique_field in clean_row:
                    lookup_val = clean_row[unique_field]
                    try:
                        existing = model_cls.objects.filter(
                            **{unique_field: lookup_val}
                        ).first()
                        if existing:
                            identical = True
                            for f, new_val in clean_row.items():
                                if f in [
                                    "created_by",
                                    "updated_by",
                                    "created_at",
                                    "updated_at",
                                ]:
                                    continue
                                old_val = getattr(existing, f, None)
                                try:
                                    old_norm = (
                                        importer._normalize_field_value(f, old_val)
                                        if hasattr(importer, "_normalize_field_value")
                                        else old_val
                                    )
                                except Exception:
                                    old_norm = old_val
                                try:
                                    new_norm = (
                                        importer._normalize_field_value(f, new_val)
                                        if hasattr(importer, "_normalize_field_value")
                                        else new_val
                                    )
                                except Exception:
                                    new_norm = new_val

                                if old_norm != new_norm:
                                    identical = False
                                    break

                            if identical:
                                skipped += 1
                            else:
                                changed = False
                                for f, new_val in clean_row.items():
                                    if getattr(existing, f, None) != new_val:
                                        setattr(existing, f, new_val)
                                        changed = True
                                if changed:
                                    try:
                                        existing.save()
                                        updated += 1
                                    except Exception as e:
                                        failed += 1
                                        errors_list.append(f"Row {idx}: {str(e)}")
                                else:
                                    skipped += 1
                        else:
                            try:
                                model_cls.objects.create(**clean_row)
                                inserted += 1
                            except Exception as e:
                                if (
                                    "duplicate" in str(e).lower()
                                    or "unique" in str(e).lower()
                                    or "integrity" in str(e).lower()
                                ):
                                    skipped += 1
                                    errors_list.append(f"Row {idx}: skipped")
                                else:
                                    failed += 1
                                    errors_list.append(f"Row {idx}: {str(e)}")
                    except Exception as e:
                        failed += 1
                        errors_list.append(f"Row {idx}: {str(e)}")
                else:
                    try:
                        model_cls.objects.create(**clean_row)
                        inserted += 1
                    except Exception as e:
                        if (
                            "duplicate" in str(e).lower()
                            or "unique" in str(e).lower()
                            or "integrity" in str(e).lower()
                        ):
                            skipped += 1
                            errors_list.append(f"Row {idx}: skipped (duplicate record)")
                        else:
                            failed += 1
                            errors_list.append(f"Row {idx}: {str(e)}")

            except Exception as e:
                failed += 1
                errors_list.append(f"Row {idx}: {str(e)}")

        message_parts = []
        if inserted > 0:
            message_parts.append(f"{inserted} records inserted successfully")
        if updated > 0:
            message_parts.append(f"{updated} records updated successfully")
        if skipped > 0:
            message_parts.append(f"{skipped} record skipped successfully")
        if failed > 0:
            message_parts.append(f"{failed} records failed")

        response = {
            "success": bool(inserted or updated or skipped),
            "total_records": total,
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            # 'failed': failed,
            "message": (
                " | ".join(message_parts) if message_parts else "No records processed"
            ),
        }

        # if errors_list:
        #     response['errors'] = errors_list[:10]  # Limit errors in response

        # Create import log for legacy processing
        self._create_import_log(model_name, user, total, response, importer)

        return response

    def _create_import_log(
        self, model_name: str, user, total: int, result: Dict, importer
    ):
        """Create import log and error records for process_rows results"""
        import_log = ImportLog.objects.create(
            user=user,
            master=model_name,
            total=total,
            success=result.get("inserted", 0) + result.get("updated", 0),
            failed=result.get("failed", 0),
            file_name=f"{model_name}_import_{user.id}",
        )

        errors = result.get("errors", [])
        if errors:
            error_records = []
            for error in errors:
                row_num = 0
                if isinstance(error, str) and "Row " in error:
                    try:
                        row_num = int(error.split("Row ")[1].split(":")[0])
                    except (IndexError, ValueError):
                        row_num = 0

                error_records.append(
                    ImportErrorRow(
                        log=import_log, row_number=row_num, error=error, row_data={}
                    )
                )

            if error_records:
                ImportErrorRow.objects.bulk_create(error_records, batch_size=100)

        return import_log
