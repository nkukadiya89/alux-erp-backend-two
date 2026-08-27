"""
Bulk database writer for efficient batch inserts
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from django.db import transaction
from django.db.models import Model

logger = logging.getLogger(__name__)


class BulkWriter:
    """
    Handles bulk database writes with transaction management
    """

    def __init__(
        self, model_class: Model, batch_size: int = 1000, use_bulk_create: bool = True
    ):
        """
        Initialize bulk writer.

        Args:
            model_class: Django model class
            batch_size: Number of records to insert per batch
            use_bulk_create: Use bulk_create for better performance
        """
        self.model_class = model_class
        self.batch_size = batch_size
        self.use_bulk_create = use_bulk_create

    @transaction.atomic
    def bulk_create(
        self, objects: List[Model], ignore_conflicts: bool = False
    ) -> tuple[int, int]:
        """
        Bulk create model instances.

        Args:
            objects: List of model instances
            ignore_conflicts: Ignore conflicts (upsert behavior)

        Returns:
            Tuple of (created_count, failed_count)
        """
        if not objects:
            return 0, 0

        try:
            if ignore_conflicts:
                created = self.model_class.objects.bulk_create(
                    objects, ignore_conflicts=True, batch_size=self.batch_size
                )
                created_count = (
                    len(created) if isinstance(created, list) else len(objects)
                )
                failed_count = len(objects) - created_count
                return created_count, failed_count
            else:
                # Try bulk create, but handle partial failures
                try:
                    created = self.model_class.objects.bulk_create(
                        objects, batch_size=self.batch_size
                    )
                    created_count = (
                        len(created) if isinstance(created, list) else len(objects)
                    )
                    return created_count, 0
                except Exception as e:
                    # If bulk_create fails, try creating one by one to get partial success
                    logger.warning(
                        f"Bulk create failed, attempting individual creates: {str(e)}"
                    )
                    created_count = 0
                    failed_count = 0

                    for obj in objects:
                        try:
                            obj.save()
                            created_count += 1
                        except Exception as individual_error:
                            failed_count += 1
                            logger.debug(
                                f"Failed to create {obj}: {str(individual_error)}"
                            )

                    return created_count, failed_count

        except Exception as e:
            logger.error(f"Error in bulk_create: {str(e)}")
            raise

    @transaction.atomic
    def bulk_update(self, objects: List[Model], update_fields: List[str]) -> int:
        """
        Bulk update model instances.

        Args:
            objects: List of model instances to update
            update_fields: List of field names to update

        Returns:
            Number of objects updated
        """
        if not objects:
            return 0

        try:
            self.model_class.objects.bulk_update(
                objects, update_fields, batch_size=self.batch_size
            )
            return len(objects)

        except Exception as e:
            logger.error(f"Error in bulk_update: {str(e)}")
            raise

    def create_in_batches(
        self, data_list: List[Dict], transform_func: Callable = None
    ) -> int:
        """
        Create objects in batches from dictionary data.

        Args:
            data_list: List of dictionaries with model field values
            transform_func: Optional function to transform dict to model instance

        Returns:
            Total number of objects created
        """
        if not data_list:
            return 0

        total_created = 0

        # Process in batches
        for i in range(0, len(data_list), self.batch_size):
            batch = data_list[i : i + self.batch_size]

            if transform_func:
                objects = [transform_func(data) for data in batch]
            else:
                objects = [self.model_class(**data) for data in batch]

            created = self.bulk_create(objects)
            total_created += created

        return total_created

    def update_or_create_batch(
        self, data_list: List[Dict], lookup_field: str, transform_func: Callable = None
    ) -> tuple[int, int]:
        """
        Update existing or create new objects in batch.

        Args:
            data_list: List of dictionaries with model field values
            lookup_field: Field to use for lookup (must be unique)
            transform_func: Optional function to transform dict to model instance

        Returns:
            Tuple of (created_count, updated_count)
        """
        if not data_list:
            return 0, 0

        created_count = 0
        updated_count = 0

        # Group by lookup field value
        lookup_values = [data[lookup_field] for data in data_list]
        existing_objects = {
            getattr(obj, lookup_field): obj
            for obj in self.model_class.objects.filter(
                **{f"{lookup_field}__in": lookup_values}
            )
        }

        to_create = []
        to_update = []

        for data in data_list:
            lookup_value = data[lookup_field]

            if transform_func:
                obj = transform_func(data)
            else:
                obj = self.model_class(**data)

            if lookup_value in existing_objects:
                # Update existing
                existing_obj = existing_objects[lookup_value]
                for key, value in data.items():
                    if key != lookup_field:
                        setattr(existing_obj, key, value)
                to_update.append(existing_obj)
            else:
                # Create new
                to_create.append(obj)

        # Bulk create new objects
        if to_create:
            created_count = self.bulk_create(to_create)

        # Bulk update existing objects
        if to_update:
            update_fields = [
                field for field in data_list[0].keys() if field != lookup_field
            ]
            updated_count = self.bulk_update(to_update, update_fields)

        return created_count, updated_count
