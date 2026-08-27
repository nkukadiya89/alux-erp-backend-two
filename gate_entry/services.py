"""
Business logic and transactional operations for Gate Entry.
No business logic in views; all write operations delegate here.
"""

import logging
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from .models import GateEntry, GateEntryItem

logger = logging.getLogger("file")


def _split_items_payload(
    items_payload: Iterable[Dict],
) -> Tuple[List[Dict], List[Dict]]:
    existing_items: List[Dict] = []
    new_items: List[Dict] = []
    for row in items_payload or []:
        if row.get("id"):
            existing_items.append(row)
        else:
            new_items.append(row)
    return existing_items, new_items


def _apply_item_updates(
    current_items: Dict,
    existing_payload: List[Dict],
) -> None:
    """Update existing GateEntryItem rows from payload. Raises ValidationError if id not found."""
    for row in existing_payload:
        item_id = str(row.get("id"))
        item = current_items.get(item_id)
        if not item:
            raise ValidationError(f"Gate entry item with id {item_id} not found.")
        for field in ["description", "unit", "qty", "purpose"]:
            if field in row:
                setattr(item, field, row[field])
        item.save()


def _sync_items(
    gate_entry: GateEntry,
    items_payload: Iterable[Dict],
) -> None:
    existing_payload, new_payload = _split_items_payload(items_payload)
    existing_ids = {str(row["id"]) for row in existing_payload if row.get("id")}

    current_items = {
        str(item.id): item
        for item in GateEntryItem.objects.filter(gate_entry=gate_entry).order_by("id")
    }

    _apply_item_updates(current_items, existing_payload)

    for item_id, item in list(current_items.items()):
        if item_id not in existing_ids:
            item.delete()

    if new_payload:
        GateEntryItem.objects.bulk_create(
            [
                GateEntryItem(
                    gate_entry=gate_entry,
                    description=row["description"],
                    unit=row["unit"],
                    qty=row["qty"],
                    purpose=row.get("purpose"),
                )
                for row in new_payload
            ]
        )


@transaction.atomic
def create_gate_entry(validated_data: Dict, user) -> GateEntry:
    items_data = validated_data.pop("items", [])

    if not items_data:
        raise ValidationError("At least one item is required.")

    if user is not None:
        validated_data["created_by"] = user
    gate_entry = GateEntry.objects.create(**validated_data)

    GateEntryItem.objects.bulk_create(
        [
            GateEntryItem(
                gate_entry=gate_entry,
                description=item["description"],
                unit=item["unit"],
                qty=item["qty"],
                purpose=item.get("purpose"),
            )
            for item in items_data
        ]
    )
    logger.info("Gate entry %s created by %s", gate_entry.gate_entry_no, user)
    return gate_entry


@transaction.atomic
def update_gate_entry(
    instance: GateEntry,
    validated_data: Dict,
    user,
) -> GateEntry:
    if instance.status == GateEntry.STATUS_CLOSE:
        raise ValidationError("Closed gate entry cannot be modified.")

    items_data = validated_data.pop("items", None)

    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.updated_by = user
    instance.updated_at = timezone.now()
    instance.save()

    if items_data is not None:
        if not items_data:
            raise ValidationError("At least one item is required.")
        _sync_items(instance, items_data)

    logger.info("Gate entry %s updated by %s", instance.gate_entry_no, user)
    return instance


def validate_can_close(gate_entry: GateEntry, outward_time=None, empty_weight=None):
    """Raise ValidationError if gate entry cannot be closed."""
    if gate_entry.status == GateEntry.STATUS_CLOSE:
        raise ValidationError("Gate entry is already closed.")

    out_time = outward_time or gate_entry.outward_time
    if out_time is None:
        raise ValidationError("Outward time is required before closing.")

    weight = (
        empty_weight if empty_weight is not None else gate_entry.empty_vehicle_weight
    )
    if weight is None:
        raise ValidationError("Empty vehicle weight is required before closing.")


@transaction.atomic
def close_gate_entry(
    instance: GateEntry,
    user,
    outward_time=None,
    empty_vehicle_weight=None,
) -> GateEntry:
    instance.refresh_from_db()
    validate_can_close(instance, outward_time, empty_vehicle_weight)

    if outward_time is not None:
        instance.outward_time = outward_time
    if empty_vehicle_weight is not None:
        instance.empty_vehicle_weight = empty_vehicle_weight
    instance.status = GateEntry.STATUS_CLOSE
    instance.updated_by = user
    instance.updated_at = timezone.now()
    instance.save(
        update_fields=[
            "outward_time",
            "empty_vehicle_weight",
            "status",
            "updated_by",
            "updated_at",
        ]
    )
    logger.info("Gate entry %s closed by %s", instance.gate_entry_no, user)
    return instance


@transaction.atomic
def bulk_archive_gate_entries(ids: List, user) -> int:
    qs = GateEntry.objects.filter(id__in=ids, deleted=False)
    updated = qs.update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Bulk archived %s gate entries by %s", updated, user)
    return updated


@transaction.atomic
def bulk_restore_gate_entries(ids: List, user) -> int:
    qs = GateEntry.objects.filter(id__in=ids, deleted=False)
    updated = qs.update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Bulk restored %s gate entries by %s", updated, user)
    return updated
