"""
Django management command to migrate comma-separated bundle IDs to proper foreign key relationships.

This command migrates existing data from the old comma-separated ID fields to the new
junction table relationships for:
- Warehouse.finalized_bundle_ids -> WarehouseBundleInward
- Warehouse.outward_bundle_ids -> WarehouseBundleOutward  
- BundleOutward.finalized_bundle_ids -> BundleOutwardInward
- BundleOutward.outward_bundle_ids -> BundleOutwardOutward

Usage:
    python manage.py migrate_bundle_relationships

Options:
    --dry-run: Show what would be migrated without making changes
    --batch-size: Number of records to process in each batch (default: 100)
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from bundle_inward.models import BundleInward
from bundle_outward.models import (
    BundleOutward,
    BundleOutwardInward,
    BundleOutwardOutward,
)
from warehouse.models import Warehouse, WarehouseBundleInward, WarehouseBundleOutward

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Migrate comma-separated bundle IDs to proper foreign key relationships.
    
    This command converts existing comma-separated bundle ID fields to the new
    junction table relationships for better data integrity and easier querying.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to process in each batch (default: 100)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed migration progress",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        verbose = options["verbose"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        try:
            # Migrate Warehouse relationships
            warehouse_stats = self.migrate_warehouse_relationships(
                dry_run, batch_size, verbose
            )

            # Migrate BundleOutward relationships
            bundle_outward_stats = self.migrate_bundle_outward_relationships(
                dry_run, batch_size, verbose
            )

            # Summary
            self.print_summary(warehouse_stats, bundle_outward_stats, dry_run)

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise CommandError(f"Migration failed: {str(e)}")

    def migrate_warehouse_relationships(self, dry_run, batch_size, verbose):
        """Migrate Warehouse finalized_bundle_ids and outward_bundle_ids."""
        self.stdout.write("\n=== Migrating Warehouse Relationships ===")

        stats = {
            "processed": 0,
            "finalized_created": 0,
            "outward_created": 0,
            "errors": 0,
        }

        # Note: In the real migration, these fields would still exist temporarily
        # For this command, we assume they exist during the transition period
        warehouses = Warehouse.objects.filter(deleted=False)

        if verbose:
            self.stdout.write(
                f"Found {warehouses.count()} warehouse records to process"
            )

        for i in range(0, warehouses.count(), batch_size):
            batch = warehouses[i : i + batch_size]

            with transaction.atomic():
                for warehouse in batch:
                    try:
                        stats["processed"] += 1

                        # Migrate finalized_bundle_ids
                        finalized_ids = self.parse_bundle_ids(
                            getattr(warehouse, "finalized_bundle_ids", "")
                        )
                        for bundle_id in finalized_ids:
                            if self.create_warehouse_bundle_relationship(
                                warehouse, bundle_id, "finalized", dry_run, verbose
                            ):
                                stats["finalized_created"] += 1

                        # Migrate outward_bundle_ids
                        outward_ids = self.parse_bundle_ids(
                            getattr(warehouse, "outward_bundle_ids", "")
                        )
                        for bundle_id in outward_ids:
                            if self.create_warehouse_bundle_relationship(
                                warehouse, bundle_id, "outward", dry_run, verbose
                            ):
                                stats["outward_created"] += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing warehouse {warehouse.id}: {str(e)}"
                        )
                        stats["errors"] += 1

        return stats

    def migrate_bundle_outward_relationships(self, dry_run, batch_size, verbose):
        """Migrate BundleOutward finalized_bundle_ids and outward_bundle_ids."""
        self.stdout.write("\n=== Migrating BundleOutward Relationships ===")

        stats = {
            "processed": 0,
            "finalized_created": 0,
            "outward_created": 0,
            "errors": 0,
        }

        bundle_outwards = BundleOutward.objects.filter(deleted=False)

        if verbose:
            self.stdout.write(
                f"Found {bundle_outwards.count()} bundle outward records to process"
            )

        for i in range(0, bundle_outwards.count(), batch_size):
            batch = bundle_outwards[i : i + batch_size]

            with transaction.atomic():
                for bundle_outward in batch:
                    try:
                        stats["processed"] += 1

                        # Migrate finalized_bundle_ids
                        finalized_ids = self.parse_bundle_ids(
                            getattr(bundle_outward, "finalized_bundle_ids", "")
                        )
                        for bundle_id in finalized_ids:
                            if self.create_bundle_outward_relationship(
                                bundle_outward, bundle_id, "finalized", dry_run, verbose
                            ):
                                stats["finalized_created"] += 1

                        # Migrate outward_bundle_ids
                        outward_ids = self.parse_bundle_ids(
                            getattr(bundle_outward, "outward_bundle_ids", "")
                        )
                        for bundle_id in outward_ids:
                            if self.create_bundle_outward_relationship(
                                bundle_outward, bundle_id, "outward", dry_run, verbose
                            ):
                                stats["outward_created"] += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing bundle outward {bundle_outward.id}: {str(e)}"
                        )
                        stats["errors"] += 1

        return stats

    def parse_bundle_ids(self, ids_string):
        """Parse comma-separated bundle IDs into a list of integers."""
        if not ids_string:
            return []

        try:
            return [
                int(bundle_id.strip())
                for bundle_id in ids_string.split(",")
                if bundle_id.strip().isdigit()
            ]
        except (ValueError, AttributeError):
            return []

    def create_warehouse_bundle_relationship(
        self, warehouse, bundle_id, relationship_type, dry_run, verbose
    ):
        """Create a warehouse-bundle relationship."""
        try:
            # Verify bundle exists
            bundle = BundleInward.objects.get(id=bundle_id, deleted=False)

            if relationship_type == "finalized":
                model_class = WarehouseBundleInward
                relation_name = "finalized"
            else:  # outward
                model_class = WarehouseBundleOutward
                relation_name = "outward"

            # Check if relationship already exists
            if model_class.objects.filter(
                warehouse=warehouse, bundle_inward=bundle
            ).exists():
                if verbose:
                    self.stdout.write(
                        f"  Warehouse {warehouse.id} -> Bundle {bundle_id} ({relation_name}) already exists"
                    )
                return False

            if not dry_run:
                model_class.objects.create(
                    warehouse=warehouse,
                    bundle_inward=bundle,
                    created_by_id=getattr(
                        settings, "SYSTEM_USER_ID", 1
                    ),  # System user or admin
                    created_at=timezone.now(),
                )

            if verbose:
                action = "Would create" if dry_run else "Created"
                self.stdout.write(
                    f"  {action} Warehouse {warehouse.id} -> Bundle {bundle_id} ({relation_name})"
                )

            return True

        except BundleInward.DoesNotExist:
            logger.warning(f"Bundle {bundle_id} not found for warehouse {warehouse.id}")
            return False
        except Exception as e:
            logger.error(f"Error creating warehouse relationship: {str(e)}")
            return False

    def create_bundle_outward_relationship(
        self, bundle_outward, bundle_id, relationship_type, dry_run, verbose
    ):
        """Create a bundle-outward-bundle relationship."""
        try:
            # Verify bundle exists
            bundle = BundleInward.objects.get(id=bundle_id, deleted=False)

            if relationship_type == "finalized":
                model_class = BundleOutwardInward
                relation_name = "finalized"
            else:  # outward
                model_class = BundleOutwardOutward
                relation_name = "outward"

            # Check if relationship already exists
            if model_class.objects.filter(
                bundle_outward=bundle_outward, bundle_inward=bundle
            ).exists():
                if verbose:
                    self.stdout.write(
                        f"  BundleOutward {bundle_outward.id} -> Bundle {bundle_id} ({relation_name}) already exists"
                    )
                return False

            if not dry_run:
                model_class.objects.create(
                    bundle_outward=bundle_outward,
                    bundle_inward=bundle,
                    created_by_id=getattr(
                        settings, "SYSTEM_USER_ID", 1
                    ),  # System user or admin
                    created_at=timezone.now(),
                )

            if verbose:
                action = "Would create" if dry_run else "Created"
                self.stdout.write(
                    f"  {action} BundleOutward {bundle_outward.id} -> Bundle {bundle_id} ({relation_name})"
                )

            return True

        except BundleInward.DoesNotExist:
            logger.warning(
                f"Bundle {bundle_id} not found for bundle outward {bundle_outward.id}"
            )
            return False
        except Exception as e:
            logger.error(f"Error creating bundle outward relationship: {str(e)}")
            return False

    def print_summary(self, warehouse_stats, bundle_outward_stats, dry_run):
        """Print migration summary."""
        self.stdout.write("\n=== Migration Summary ===")

        action = "Would be migrated" if dry_run else "Migrated"

        self.stdout.write(f"\nWarehouse Records:")
        self.stdout.write(f'  - Processed: {warehouse_stats["processed"]}')
        self.stdout.write(
            f'  - Finalized relationships {action.lower()}: {warehouse_stats["finalized_created"]}'
        )
        self.stdout.write(
            f'  - Outward relationships {action.lower()}: {warehouse_stats["outward_created"]}'
        )
        self.stdout.write(f'  - Errors: {warehouse_stats["errors"]}')

        self.stdout.write(f"\nBundleOutward Records:")
        self.stdout.write(f'  - Processed: {bundle_outward_stats["processed"]}')
        self.stdout.write(
            f'  - Finalized relationships {action.lower()}: {bundle_outward_stats["finalized_created"]}'
        )
        self.stdout.write(
            f'  - Outward relationships {action.lower()}: {bundle_outward_stats["outward_created"]}'
        )
        self.stdout.write(f'  - Errors: {bundle_outward_stats["errors"]}')

        total_relationships = (
            warehouse_stats["finalized_created"]
            + warehouse_stats["outward_created"]
            + bundle_outward_stats["finalized_created"]
            + bundle_outward_stats["outward_created"]
        )

        self.stdout.write(
            f"\nTotal relationships {action.lower()}: {total_relationships}"
        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nDry run completed successfully! Run without --dry-run to apply changes."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration completed successfully!"))

        if warehouse_stats["errors"] > 0 or bundle_outward_stats["errors"] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\nWarning: {warehouse_stats["errors"] + bundle_outward_stats["errors"]} errors encountered. Check logs for details.'
                )
            )
