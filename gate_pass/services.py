"""
Business logic and transactional operations for Gate Pass.
"""

import logging
from typing import Dict, Iterable, List, Tuple

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import GatePass, GatePassItem

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


def _sync_items(
    gate_pass: GatePass,
    items_payload: Iterable[Dict],
) -> None:
    existing_payload, new_payload = _split_items_payload(items_payload)
    existing_ids = {str(row["id"]) for row in existing_payload if row.get("id")}

    current_items = {
        str(item.id): item
        for item in GatePassItem.objects.filter(gate_pass=gate_pass).order_by("id")
    }

    # Update existing
    for row in existing_payload:
        item_id = str(row.get("id"))
        item = current_items.get(item_id)
        if not item:
            raise ValidationError(f"Gate pass item with id {item_id} not found.")

        # If gate pass is linked to PO, description cannot be edited
        if gate_pass.po_id is not None and "description" in row:
            row.pop("description")

        for field in ["description", "unit", "qty", "purpose"]:
            if field in row:
                setattr(item, field, row[field])
        item.save()

    # Delete removed
    for item_id, item in current_items.items():
        if item_id not in existing_ids:
            item.delete()

    # Create new
    GatePassItem.objects.bulk_create(
        [
            GatePassItem(
                gate_pass=gate_pass,
                description=row["description"],
                unit=row["unit"],
                qty=row["qty"],
                purpose=row.get("purpose"),
            )
            for row in new_payload
        ]
    )


@transaction.atomic
def create_gate_pass(validated_data: Dict, user) -> GatePass:
    items_data = validated_data.pop("items", [])

    if not items_data:
        raise ValidationError("At least one item is required.")

    gate_pass = GatePass.objects.create(
        status=GatePass.STATUS_DRAFT,
        created_by=user,
        **validated_data,
    )

    GatePassItem.objects.bulk_create(
        [
            GatePassItem(
                gate_pass=gate_pass,
                description=item["description"],
                unit=item["unit"],
                qty=item["qty"],
                purpose=item.get("purpose"),
            )
            for item in items_data
        ]
    )

    return gate_pass


@transaction.atomic
def update_gate_pass(
    instance: GatePass,
    validated_data: Dict,
    user,
) -> GatePass:
    items_data = validated_data.pop("items", None)

    if instance.status == GatePass.STATUS_CLOSED:
        raise ValidationError("Closed gate pass cannot be modified.")

    for attr, value in validated_data.items():
        setattr(instance, attr, value)

    instance.updated_by = user
    instance.updated_at = timezone.now()
    instance.save()

    if items_data is not None:
        if not items_data:
            raise ValidationError("At least one item is required.")
        _sync_items(instance, items_data)

    return instance


@transaction.atomic
def submit_gate_pass(gate_pass: GatePass, user) -> GatePass:
    gate_pass.refresh_from_db()

    if gate_pass.deleted:
        raise ValidationError("Deleted gate pass cannot be submitted.")

    if gate_pass.status != GatePass.STATUS_DRAFT:
        raise ValidationError("Only draft gate passes can be submitted.")

    if not gate_pass.items.exists():
        raise ValidationError("Cannot submit without at least one item.")

    if gate_pass.type == GatePass.TYPE_NON_RETURNABLE:
        gate_pass.status = GatePass.STATUS_CLOSED
    else:
        gate_pass.status = GatePass.STATUS_PENDING

    gate_pass.updated_by = user
    gate_pass.updated_at = timezone.now()
    gate_pass.save(update_fields=["status", "updated_by", "updated_at"])

    logger.info("Gate pass %s submitted by %s", gate_pass.gate_pass_no, user)
    return gate_pass


@transaction.atomic
def mark_gate_pass_in_process(gate_pass: GatePass, user) -> GatePass:
    gate_pass.refresh_from_db()

    if gate_pass.type != GatePass.TYPE_RETURNABLE:
        raise ValidationError("Only returnable gate passes can be marked in process.")

    if gate_pass.status != GatePass.STATUS_PENDING:
        raise ValidationError("Gate pass must be in PENDING status.")

    gate_pass.status = GatePass.STATUS_IN_PROCESS
    gate_pass.updated_by = user
    gate_pass.updated_at = timezone.now()
    gate_pass.save(update_fields=["status", "updated_by", "updated_at"])

    logger.info("Gate pass %s marked IN_PROCESS by %s", gate_pass.gate_pass_no, user)
    return gate_pass


@transaction.atomic
def mark_gate_pass_returned(gate_pass: GatePass, user) -> GatePass:
    gate_pass.refresh_from_db()

    if gate_pass.type != GatePass.TYPE_RETURNABLE:
        raise ValidationError("Only returnable gate passes can be marked returned.")

    if gate_pass.status != GatePass.STATUS_IN_PROCESS:
        raise ValidationError("Gate pass must be in IN_PROCESS status.")

    gate_pass.status = GatePass.STATUS_CLOSED
    gate_pass.updated_by = user
    gate_pass.updated_at = timezone.now()
    gate_pass.save(update_fields=["status", "updated_by", "updated_at"])

    logger.info(
        "Gate pass %s marked CLOSED (returned) by %s", gate_pass.gate_pass_no, user
    )
    return gate_pass


def load_po_items(po_id) -> List[Dict]:
    """
    Return list of PO items to prefill gate pass items.
    Validates PO existence when PurchaseOrder model is available.
    """
    try:
        from procurement.models import PurchaseOrderItem  # type: ignore

        try:
            from procurement.models import PurchaseOrder  # type: ignore

            if not PurchaseOrder.objects.filter(id=po_id).exists():
                raise ValidationError("Purchase order not found.")
        except ImportError:
            pass
    except Exception as exc:  # pragma: no cover - dependent on procurement app
        if isinstance(exc, ValidationError):
            raise
        logger.error("Failed to import PurchaseOrderItem: %s", exc, exc_info=True)
        raise ValidationError("Purchase order items are not available.") from exc

    po_items = (
        PurchaseOrderItem.objects.filter(purchase_order_id=po_id)
        .order_by("id")
        .values("id", "description", "unit", "qty")
    )

    return [
        {
            "source_po_item_id": row["id"],
            "description": row["description"],
            "unit": row["unit"],
            "qty": row["qty"],
            "purpose": "",
        }
        for row in po_items
    ]


@transaction.atomic
def bulk_archive_gate_passes(ids: List[str], user) -> int:
    """Archive only CLOSED gate passes; skip others per ERP rule."""
    qs = GatePass.objects.filter(
        id__in=ids, deleted=False, status=GatePass.STATUS_CLOSED
    )
    updated = qs.update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Bulk archived %s gate passes by %s", updated, user)
    return updated


@transaction.atomic
def bulk_restore_gate_passes(ids: List[str], user) -> int:
    qs = GatePass.objects.filter(id__in=ids, deleted=False)
    updated = qs.update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Bulk restored %s gate passes by %s", updated, user)
    return updated
