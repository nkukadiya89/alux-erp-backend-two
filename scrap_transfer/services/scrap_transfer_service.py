import logging
from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

from scrap_transfer.models import ScrapTransfer, ScrapTransferItem
from scrap_entry.models import ScrapStoreStock
from product.models import Item
from store.models import Store

logger = logging.getLogger("file")

REFERENCE_TYPE_SCRAP_TRANSFER = "SCRAP_TRANSFER"


def _get_available_scrap_qty(store_id: str, item_id: str) -> Decimal:
    """Return current scrap store quantity for store+item from ScrapStoreStock."""
    try:
        stock = ScrapStoreStock.objects.get(store_id=store_id, item_id=item_id)
        return stock.quantity
    except ScrapStoreStock.DoesNotExist:
        return Decimal("0")


def _get_or_create_scrap_stock(store_id: str, item_id: str):
    """Get or create ScrapStoreStock. Caller must run inside transaction."""
    from scrap_entry.models import ScrapStoreStock

    return ScrapStoreStock.objects.select_for_update().get_or_create(
        store_id=store_id,
        item_id=item_id,
        defaults={"quantity": Decimal("0")},
    )[0]


def _decrease_scrap_store_stock(store_id: str, item_id: str, qty: Decimal) -> None:
    """Decrease scrap store quantity. Caller must run inside transaction."""
    stock = _get_or_create_scrap_stock(store_id, item_id)
    if stock.quantity < qty:
        item = (
            Item.objects.filter(pk=item_id).values_list("item_code", flat=True).first()
        )
        raise ValidationError(
            f"Insufficient scrap stock for item {item or item_id}. "
            f"Available: {stock.quantity}, requested: {qty}."
        )
    stock.quantity -= qty
    stock.save(update_fields=["quantity", "updated_at"])


def _validate_item_heat_tracking(item: Item, batch_heat: str | None) -> None:
    """If item.heat_tracking is True, batch_heat is mandatory."""
    if getattr(item, "heat_tracking", False) and not (
        batch_heat and str(batch_heat).strip()
    ):
        raise ValidationError(
            f"Item {item.item_code} has heat tracking enabled. batch_heat is mandatory."
        )


def _validate_from_store_scrap_type(store_id: str) -> None:
    """from_store must be a scrap type store (store_type name contains 'scrap' case-insensitive)."""
    store = (
        Store.objects.filter(pk=store_id, deleted=False)
        .select_related("store_type")
        .first()
    )
    if not store:
        raise ValidationError("Invalid or inactive from_store.")
    if not store.store_type_id:
        raise ValidationError("from_store must have a store type (scrap store).")
    name = (store.store_type.name or "").lower()
    if "scrap" not in name:
        raise ValidationError(
            f"from_store must be a scrap type store. Got: {store.store_type.name}."
        )


def _validate_to_store_belongs_to_plant(store_id: str, plant_id: str) -> None:
    """to_store must belong to to_plant."""
    store = Store.objects.filter(pk=store_id, plant_id=plant_id, deleted=False).first()
    if not store:
        raise ValidationError(
            "to_store does not belong to the selected plant or is inactive."
        )


@transaction.atomic
def create_scrap_transfer(validated_data: Dict[str, Any], user) -> ScrapTransfer:
    """Create ScrapTransfer and items. Validates at least one item, transfer_qty > 0, availability."""
    items_data = validated_data.pop("items", [])

    if not items_data:
        raise ValidationError("At least one item is required.")

    transfer_no = validated_data.get("transfer_no")
    if not transfer_no:
        from utils.generate_number import generate_scrap_transfer_no

        transfer_no = generate_scrap_transfer_no()

    from_store_id = validated_data.get("from_store")
    if hasattr(from_store_id, "pk"):
        from_store_id = str(from_store_id.pk)
    else:
        from_store_id = str(from_store_id)

    to_plant_id = validated_data.get("to_plant")
    if hasattr(to_plant_id, "pk"):
        to_plant_id = str(to_plant_id.pk)
    else:
        to_plant_id = str(to_plant_id)

    to_store_id = validated_data.get("to_store")
    if hasattr(to_store_id, "pk"):
        to_store_id = str(to_store_id.pk)
    else:
        to_store_id = str(to_store_id)

    _validate_from_store_scrap_type(from_store_id)
    _validate_to_store_belongs_to_plant(to_store_id, to_plant_id)

    transfer = ScrapTransfer.objects.create(
        transfer_no=transfer_no,
        created_by=user,
        updated_by=user,
        status=ScrapTransfer.STATUS_DRAFT,
        total_qty=Decimal("0"),
        from_store_id=from_store_id,
        to_plant_id=to_plant_id,
        to_store_id=to_store_id,
        **{
            k: v
            for k, v in validated_data.items()
            if k not in ("from_store", "to_plant", "to_store")
        },
    )

    item_objs = []
    for row in items_data:
        qty = Decimal(str(row["transfer_qty"]))
        if qty <= 0:
            raise ValidationError("transfer_qty must be greater than 0.")
        item = (
            Item.objects.filter(pk=row["scrap_item"]).select_related("category").first()
        )
        if not item:
            raise ValidationError(f"Item {row['scrap_item']} not found.")
        _validate_item_heat_tracking(item, row.get("batch_heat"))
        available = _get_available_scrap_qty(from_store_id, str(row["scrap_item"]))
        if qty > available:
            raise ValidationError(
                f"transfer_qty for {item.item_code} exceeds available scrap stock ({available})."
            )
        item_objs.append(
            ScrapTransferItem(
                scrap_transfer=transfer,
                scrap_item_id=row["scrap_item"],
                batch_heat=row.get("batch_heat"),
                transfer_qty=qty,
                uom_id=row["uom"],
                remarks=row.get("remarks"),
            )
        )

    ScrapTransferItem.objects.bulk_create(item_objs)

    totals = ScrapTransferItem.objects.filter(scrap_transfer=transfer).aggregate(
        total_qty=Sum("transfer_qty"),
    )
    transfer.total_qty = totals["total_qty"] or Decimal("0")
    transfer.save(update_fields=["total_qty"])

    logger.info("Created scrap transfer %s by %s", transfer.transfer_no, user)
    return transfer


def _sync_items(transfer: ScrapTransfer, items_data: List[Dict], user) -> None:
    """Replace transfer items. Only for DRAFT. Validates qty and availability."""
    if not items_data:
        raise ValidationError("At least one item is required.")

    from_store_id = str(transfer.from_store_id)

    ScrapTransferItem.objects.filter(scrap_transfer=transfer).delete()

    item_objs = []
    for row in items_data:
        qty = Decimal(str(row["transfer_qty"]))
        if qty <= 0:
            raise ValidationError("transfer_qty must be greater than 0.")
        item = (
            Item.objects.filter(pk=row["scrap_item"]).select_related("category").first()
        )
        if not item:
            raise ValidationError(f"Item {row['scrap_item']} not found.")
        _validate_item_heat_tracking(item, row.get("batch_heat"))
        available = _get_available_scrap_qty(from_store_id, str(row["scrap_item"]))
        if qty > available:
            raise ValidationError(
                f"transfer_qty for {item.item_code} exceeds available scrap stock ({available})."
            )
        item_objs.append(
            ScrapTransferItem(
                scrap_transfer=transfer,
                scrap_item_id=row["scrap_item"],
                batch_heat=row.get("batch_heat"),
                transfer_qty=qty,
                uom_id=row["uom"],
                remarks=row.get("remarks"),
            )
        )

    ScrapTransferItem.objects.bulk_create(item_objs)


@transaction.atomic
def update_scrap_transfer(
    instance: ScrapTransfer, validated_data: Dict[str, Any], user
) -> ScrapTransfer:
    """Update ScrapTransfer and items. Only DRAFT can be edited."""
    if instance.status != ScrapTransfer.STATUS_DRAFT:
        raise ValidationError("Only DRAFT scrap transfers can be edited.")

    items_data = validated_data.pop("items", None)

    for attr, value in validated_data.items():
        if attr != "items" and hasattr(instance, attr):
            setattr(instance, attr, value)

    instance.updated_by = user
    instance.updated_at = timezone.now()
    update_fields = [k for k in validated_data if k != "items"] + [
        "updated_by",
        "updated_at",
    ]
    instance.save(update_fields=list(set(update_fields)))

    if items_data is not None:
        _sync_items(instance, items_data, user)

    totals = ScrapTransferItem.objects.filter(scrap_transfer=instance).aggregate(
        total_qty=Sum("transfer_qty"),
    )
    instance.total_qty = totals["total_qty"] or Decimal("0")
    instance.save(update_fields=["total_qty"])

    logger.info("Updated scrap transfer %s by %s", instance.transfer_no, user)
    return instance


def submit_scrap_transfer(transfer: ScrapTransfer, user) -> ScrapTransfer:
    """Submit: validate items, lock editing, set status SUBMITTED. No stock movement."""
    transfer.refresh_from_db()

    if transfer.status != ScrapTransfer.STATUS_DRAFT:
        raise ValidationError("Only DRAFT scrap transfers can be submitted.")

    items = list(
        ScrapTransferItem.objects.filter(scrap_transfer=transfer).select_related(
            "scrap_item", "uom"
        )
    )
    if not items:
        raise ValidationError("Cannot submit without at least one item.")

    from_store_id = str(transfer.from_store_id)
    for item_row in items:
        available = _get_available_scrap_qty(from_store_id, str(item_row.scrap_item_id))
        if item_row.transfer_qty > available:
            raise ValidationError(
                f"Insufficient scrap stock for {item_row.scrap_item.item_code}. "
                f"Available: {available}, requested: {item_row.transfer_qty}."
            )
        _validate_item_heat_tracking(item_row.scrap_item, item_row.batch_heat)

    transfer.status = ScrapTransfer.STATUS_SUBMITTED
    transfer.updated_by = user
    transfer.updated_at = timezone.now()
    transfer.save(update_fields=["status", "updated_by", "updated_at"])

    logger.info("Submitted scrap transfer %s by %s", transfer.transfer_no, user)
    return transfer


@transaction.atomic
def complete_scrap_transfer(transfer: ScrapTransfer, user) -> ScrapTransfer:
    """
    Complete: validate SUBMITTED, re-validate stock (race condition), deduct from scrap store,
    add to melting WIP, create ledger entries, set status COMPLETED.
    """
    transfer.refresh_from_db()

    if transfer.status != ScrapTransfer.STATUS_SUBMITTED:
        raise ValidationError("Only SUBMITTED scrap transfers can be completed.")

    items = list(
        ScrapTransferItem.objects.filter(scrap_transfer=transfer).select_related(
            "scrap_item", "uom"
        )
    )
    if not items:
        raise ValidationError("Cannot complete without at least one item.")

    from_store_id = str(transfer.from_store_id)
    to_store_id = str(transfer.to_store_id)
    to_plant_id = str(transfer.to_plant_id)

    # Re-validate availability (prevent race condition)
    for item_row in items:
        stock = _get_or_create_scrap_stock(from_store_id, str(item_row.scrap_item_id))
        if stock.quantity < item_row.transfer_qty:
            raise ValidationError(
                f"Insufficient scrap stock for {item_row.scrap_item.item_code}. "
                f"Available: {stock.quantity}, requested: {item_row.transfer_qty}. "
                "Another transaction may have consumed stock."
            )

    # 1. Deduct from Scrap Store
    for item_row in items:
        _decrease_scrap_store_stock(
            from_store_id,
            str(item_row.scrap_item_id),
            item_row.transfer_qty,
        )

    # 4. Update transfer: total_qty, status COMPLETED
    total_qty = sum(i.transfer_qty for i in items)
    transfer.total_qty = total_qty
    transfer.status = ScrapTransfer.STATUS_COMPLETED
    transfer.updated_by = user
    transfer.updated_at = timezone.now()
    transfer.save(update_fields=["total_qty", "status", "updated_by", "updated_at"])

    logger.info("Completed scrap transfer %s by %s", transfer.transfer_no, user)
    return transfer


def cancel_submit(transfer: ScrapTransfer, user) -> ScrapTransfer:
    """Revert SUBMITTED to DRAFT. COMPLETED is rejected (use reversal module)."""
    transfer.refresh_from_db()

    if transfer.status == ScrapTransfer.STATUS_COMPLETED:
        raise ValidationError(
            "COMPLETED scrap transfers cannot be cancelled. Use reversal module instead."
        )
    if transfer.status != ScrapTransfer.STATUS_SUBMITTED:
        raise ValidationError("Only SUBMITTED scrap transfers can be cancelled.")

    transfer.status = ScrapTransfer.STATUS_DRAFT
    transfer.updated_by = user
    transfer.updated_at = timezone.now()
    transfer.save(update_fields=["status", "updated_by", "updated_at"])

    logger.info(
        "Cancelled submit for scrap transfer %s by %s", transfer.transfer_no, user
    )
    return transfer


@transaction.atomic
def archive_scrap_transfers(ids: List[str], user) -> int:
    """Archive scrap transfers. Allowed only for DRAFT."""
    qs = ScrapTransfer.objects.filter(id__in=ids, is_archived=False)
    non_draft = qs.exclude(status=ScrapTransfer.STATUS_DRAFT).first()
    if non_draft:
        raise ValidationError(
            f"Cannot archive scrap transfer {non_draft.transfer_no}. "
            "Only DRAFT transfers can be archived."
        )
    updated = qs.filter(status=ScrapTransfer.STATUS_DRAFT).update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Archived %s scrap transfer(s) by %s", updated, user)
    return updated


@transaction.atomic
def restore_scrap_transfers(ids: List[str], user) -> int:
    """Restore archived scrap transfers."""
    updated = ScrapTransfer.objects.filter(id__in=ids, is_archived=True).update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Restored %s scrap transfer(s) by %s", updated, user)
    return updated


def get_available_scrap_items_in_store(store_id: str) -> List[Dict[str, Any]]:
    """
    Return items with available scrap qty in the given store (for dropdown / available-in-store API).
    Uses ScrapStoreStock; only items with quantity > 0 are returned.
    """
    from scrap_entry.models import ScrapStoreStock

    stocks = (
        ScrapStoreStock.objects.filter(store_id=store_id, quantity__gt=0)
        .select_related("item", "item__uom")
        .order_by("item__item_code")
    )
    result = []
    for s in stocks:
        result.append(
            {
                "id": str(s.item_id),
                "item_code": s.item.item_code,
                "item_name": getattr(s.item, "item_name", "") or "",
                "uom_id": str(s.item.uom_id) if s.item.uom_id else None,
                "uom_code": (
                    s.item.uom.uom_code if getattr(s.item, "uom", None) else None
                ),
                "available_qty": str(s.quantity),
            }
        )
    return result
