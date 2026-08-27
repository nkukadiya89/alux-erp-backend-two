# bulk_import/writers/bulk_writer.py
from typing import Any, Dict, List, Type

from django.db import models, transaction


class BulkWriter:
    """Bulk database writer for import operations"""

    @transaction.atomic
    def write(self, model: Type[models.Model], rows: List[Dict[str, Any]]) -> int:
        """
        Bulk write rows to database with INSERT/UPDATE logic
        Returns number of successfully processed records
        """
        if not rows:
            return 0

        to_create = []
        to_update = []
        success_count = 0

        # Separate rows by action
        for row in rows:
            action = row.get("_action", "INSERT")

            # Remove metadata fields
            clean_row = {k: v for k, v in row.items() if not k.startswith("_")}

            if action == "INSERT":
                try:
                    # Resolve foreign keys before creating
                    resolved_row = self._resolve_foreign_keys(model, clean_row)
                    to_create.append(model(**resolved_row))
                except Exception as e:
                    # Log error but continue processing
                    print(f"Error preparing row for INSERT: {e}")
                    continue

            elif action == "UPDATE":
                to_update.append(clean_row)

        # Bulk create new records
        if to_create:
            try:
                created_objects = model.objects.bulk_create(to_create, batch_size=500)
                success_count += len(created_objects)
            except Exception as e:
                print(f"Bulk create error: {e}")
                # Try individual creates as fallback
                for obj in to_create:
                    try:
                        obj.save()
                        success_count += 1
                    except Exception:
                        pass  # Skip failed records

        # Process updates
        for row in to_update:
            try:
                # Find the unique field to identify the record
                unique_field = self._get_unique_field(model, row)
                if unique_field and unique_field in row:
                    # Resolve foreign keys
                    resolved_row = self._resolve_foreign_keys(model, row)

                    # Update the record
                    updated = model.objects.filter(
                        **{unique_field: row[unique_field]}
                    ).update(**resolved_row)
                    if updated > 0:
                        success_count += 1
            except Exception as e:
                print(f"Update error for row {row}: {e}")
                continue

        return success_count

    def _get_unique_field(self, model: Type[models.Model], row: Dict[str, Any]) -> str:
        """Get the unique field for the model to use for updates"""
        # Try common unique fields in order of preference
        common_unique_fields = [
            "code",
            "customer_number",
            "gstin_number",
            "email",
            "name",
        ]

        for field in common_unique_fields:
            if hasattr(model, field) and field in row:
                return field

        # If no common unique field, use primary key
        return model._meta.pk.name

    def _resolve_foreign_keys(
        self, model: Type[models.Model], row: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve foreign key string values to actual model instances"""
        resolved_row = row.copy()

        # Get all foreign key fields
        for field in model._meta.get_fields():
            if isinstance(field, models.ForeignKey) and field.name in row:
                fk_value = row[field.name]

                if fk_value and isinstance(fk_value, str):
                    try:
                        # Try to find the related object
                        related_model = field.related_model

                        # Try common lookup fields
                        lookup_fields = ["name", "code", "username"]
                        related_obj = None

                        for lookup_field in lookup_fields:
                            if hasattr(related_model, lookup_field):
                                try:
                                    related_obj = related_model.objects.get(
                                        **{lookup_field: fk_value}
                                    )
                                    break
                                except related_model.DoesNotExist:
                                    continue

                        if related_obj:
                            resolved_row[field.name] = related_obj
                        else:
                            # Remove the field if we can't resolve it
                            resolved_row.pop(field.name, None)

                    except Exception as e:
                        print(f"Error resolving FK {field.name}: {e}")
                        # Remove the field if we can't resolve it
                        resolved_row.pop(field.name, None)

        return resolved_row
