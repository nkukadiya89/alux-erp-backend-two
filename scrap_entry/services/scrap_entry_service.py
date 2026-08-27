"""
Scrap Entry service layer.
Business logic and atomic transactions for create, update, post, mark-transferred, archive.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

from scrap_entry.models import (
    ScrapEntry,
    ScrapEntryItem,
    ScrapStoreStock,
    ScrapType,
)
from product.models import Item
from store.models import Store

logger = logging.getLogger("file")


def _get_or_create_scrap_stock(store_id, item_id) -> ScrapStoreStock:
    """Get or create ScrapStoreStock for store+item. Caller must run inside transaction."""
    stock, _ = ScrapStoreStock.objects.select_for_update().get_or_create(
        store_id=store_id,
        item_id=item_id,
        defaults={"quantity": Decimal("0")},
    )
    return stock


def _increase_scrap_store_stock(store_id: str, item_id: str, qty: Decimal) -> None:
    """Increase scrap store quantity. Caller must run inside transaction."""
    stock = _get_or_create_scrap_stock(store_id, item_id)
    stock.quantity += qty
    stock.save(update_fields=["quantity", "updated_at"])


def _create_inventory_ledger_entry(scrap_entry: ScrapEntry, user) -> None:
    """
    Create inventory ledger entry for scrap entry (stock IN movement).
    Hook for ledger module integration; no-op if ledger not present.
    """
    try:
        logger.info(
            "Scrap entry ledger hook: entry_no=%s total_qty=%s",
            scrap_entry.entry_no,
            scrap_entry.total_qty,
        )
    except Exception as e:
        logger.warning("Scrap entry ledger hook failed (non-blocking): %s", e)


def _validate_item_heat_tracking(item: Item, batch_heat: str | None) -> None:
    """If item.heat_tracking is True, batch_heat is mandatory."""
    if item.heat_tracking and not (batch_heat and str(batch_heat).strip()):
        raise ValidationError(
            f"Item {item.item_code} has heat tracking enabled. batch_heat is mandatory."
        )


def _validate_scrap_type_matches_item(scrap_type: ScrapType, item: Item) -> None:
    """scrap_type must match item category: if scrap_type has category, item.category must match."""
    if (
        scrap_type.category_id is not None
        and item.category_id != scrap_type.category_id
    ):
        raise ValidationError(
            f"Scrap type {scrap_type.code} does not match item category for {item.item_code}."
        )


def _validate_store_belongs_to_plant(store_id: str, plant_id: str) -> None:
    """Store must belong to the given plant."""
    store = Store.objects.filter(pk=store_id, plant_id=plant_id, deleted=False).first()
    if not store:
        raise ValidationError(
            "Store does not belong to the selected plant or is inactive."
        )


@transaction.atomic
def create_scrap_entry(validated_data: Dict[str, Any], user) -> ScrapEntry:
    """Create ScrapEntry and items. Validates at least one item, qty > 0, heat tracking, store/plant."""
    items_data = validated_data.pop("items", [])

    if not items_data:
        raise ValidationError("At least one item is required.")

    entry_no = validated_data.get("entry_no")
    if not entry_no:
        from utils.generate_number import generate_scrap_entry_no

        entry_no = generate_scrap_entry_no()

    plant_id = validated_data.get("plant")
    if isinstance(plant_id, (str, type(None))):
        plant_id = plant_id
    else:
        plant_id = getattr(plant_id, "id", plant_id)

    scrap_entry = ScrapEntry.objects.create(
        entry_no=entry_no,
        created_by=user,
        updated_by=user,
        status=ScrapEntry.STATUS_DRAFT,
        total_qty=Decimal("0"),
        **validated_data,
    )

    item_objs = []
    for row in items_data:
        qty = Decimal(str(row["qty"]))
        if qty <= 0:
            raise ValidationError("qty must be greater than 0.")
        item = Item.objects.select_related("category").get(pk=row["item"])
        scrap_type = ScrapType.objects.get(pk=row["scrap_type"])
        store_id = row["store"]
        _validate_scrap_type_matches_item(scrap_type, item)
        _validate_store_belongs_to_plant(store_id, scrap_entry.plant_id)
        _validate_item_heat_tracking(item, row.get("batch_heat"))

        process_id = row.get("process")
        item_objs.append(
            ScrapEntryItem(
                scrap_entry=scrap_entry,
                item_id=row["item"],
                scrap_type_id=row["scrap_type"],
                qty=qty,
                uom_id=row["uom"],
                process_id=process_id,
                from_process=row.get("from_process"),
                store_id=store_id,
                batch_heat=row.get("batch_heat"),
                remarks=row.get("remarks"),
            )
        )

    ScrapEntryItem.objects.bulk_create(item_objs)

    totals = ScrapEntryItem.objects.filter(scrap_entry=scrap_entry).aggregate(
        total_qty=Sum("qty"),
    )
    scrap_entry.total_qty = totals["total_qty"] or Decimal("0")
    scrap_entry.save(update_fields=["total_qty"])

    logger.info("Created scrap entry %s by %s", scrap_entry.entry_no, user)
    return scrap_entry


def _sync_items(scrap_entry: ScrapEntry, items_data: List[Dict], user) -> None:
    """Replace entry items with new set. Only for DRAFT. Validates qty, heat, store/plant."""
    if not items_data:
        raise ValidationError("At least one item is required.")

    ScrapEntryItem.objects.filter(scrap_entry=scrap_entry).delete()

    item_objs = []
    for row in items_data:
        qty = Decimal(str(row["qty"]))
        if qty <= 0:
            raise ValidationError("qty must be greater than 0.")
        item = Item.objects.select_related("category").get(pk=row["item"])
        scrap_type = ScrapType.objects.get(pk=row["scrap_type"])
        store_id = row["store"]
        _validate_scrap_type_matches_item(scrap_type, item)
        _validate_store_belongs_to_plant(store_id, scrap_entry.plant_id)
        _validate_item_heat_tracking(item, row.get("batch_heat"))

        process_id = row.get("process")
        item_objs.append(
            ScrapEntryItem(
                scrap_entry=scrap_entry,
                item_id=row["item"],
                scrap_type_id=row["scrap_type"],
                qty=qty,
                uom_id=row["uom"],
                process_id=process_id,
                from_process=row.get("from_process"),
                store_id=store_id,
                batch_heat=row.get("batch_heat"),
                remarks=row.get("remarks"),
            )
        )

    ScrapEntryItem.objects.bulk_create(item_objs)


@transaction.atomic
def update_scrap_entry(
    instance: ScrapEntry, validated_data: Dict[str, Any], user
) -> ScrapEntry:
    """Update ScrapEntry and items. Only DRAFT can be edited."""
    if instance.status != ScrapEntry.STATUS_DRAFT:
        raise ValidationError("Only DRAFT scrap entries can be edited.")

    items_data = validated_data.pop("items", None)

    for attr, value in validated_data.items():
        if attr != "items":
            setattr(instance, attr, value)

    instance.updated_by = user
    instance.updated_at = timezone.now()
    update_fields = [k for k in validated_data if k != "items"] + [
        "updated_by",
        "updated_at",
    ]
    instance.save(update_fields=update_fields)

    if items_data is not None:
        _sync_items(instance, items_data, user)

    totals = ScrapEntryItem.objects.filter(scrap_entry=instance).aggregate(
        total_qty=Sum("qty"),
    )
    instance.total_qty = totals["total_qty"] or Decimal("0")
    instance.save(update_fields=["total_qty"])

    logger.info("Updated scrap entry %s by %s", instance.entry_no, user)
    return instance


@transaction.atomic
def post_scrap_entry(scrap_entry: ScrapEntry, user) -> ScrapEntry:
    """
    Post scrap entry: validate DRAFT, validate items, increase scrap store stock,
    create ledger entry, set status POSTED, compute total_qty.
    """
    scrap_entry.refresh_from_db()

    if scrap_entry.status != ScrapEntry.STATUS_DRAFT:
        raise ValidationError("Only DRAFT scrap entries can be posted.")

    items = list(
        ScrapEntryItem.objects.filter(scrap_entry=scrap_entry).select_related(
            "item", "store", "scrap_type", "process", "uom"
        )
    )
    if not items:
        raise ValidationError("Cannot post without at least one item.")

    for item_row in items:
        _validate_store_belongs_to_plant(
            str(item_row.store_id),
            str(scrap_entry.plant_id),
        )
        _validate_item_heat_tracking(item_row.item, item_row.batch_heat)

    # 1. Increase scrap store stock per item
    for item_row in items:
        _increase_scrap_store_stock(
            str(item_row.store_id),
            str(item_row.item_id),
            item_row.qty,
        )

    # 2. Create inventory ledger entry (IN movement)
    total_qty = sum(i.qty for i in items)
    scrap_entry.total_qty = total_qty
    _create_inventory_ledger_entry(scrap_entry, user)

    # 3. Update status = POSTED
    scrap_entry.status = ScrapEntry.STATUS_POSTED
    scrap_entry.updated_by = user
    scrap_entry.updated_at = timezone.now()
    scrap_entry.save(update_fields=["total_qty", "status", "updated_by", "updated_at"])

    logger.info("Posted scrap entry %s by %s", scrap_entry.entry_no, user)
    return scrap_entry


def mark_scrap_transferred(scrap_entry: ScrapEntry, user) -> ScrapEntry:
    """Mark scrap entry as TRANSFERRED. Only POSTED entries."""
    scrap_entry.refresh_from_db()

    if scrap_entry.status != ScrapEntry.STATUS_POSTED:
        raise ValidationError("Only POSTED scrap entries can be marked as transferred.")

    scrap_entry.status = ScrapEntry.STATUS_TRANSFERRED
    scrap_entry.updated_by = user
    scrap_entry.updated_at = timezone.now()
    scrap_entry.save(update_fields=["status", "updated_by", "updated_at"])

    logger.info(
        "Marked scrap entry %s as transferred by %s", scrap_entry.entry_no, user
    )
    return scrap_entry


@transaction.atomic
def archive_scrap_entries(ids: List[str], user) -> int:
    """Archive scrap entries. Allowed only for DRAFT."""
    qs = ScrapEntry.objects.filter(id__in=ids, is_archived=False)
    non_draft = qs.exclude(status=ScrapEntry.STATUS_DRAFT).first()
    if non_draft:
        raise ValidationError(
            f"Cannot archive scrap entry {non_draft.entry_no}. "
            "Only DRAFT entries can be archived."
        )
    updated = qs.filter(status=ScrapEntry.STATUS_DRAFT).update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Archived %s scrap entry(ies) by %s", updated, user)
    return updated


@transaction.atomic
def restore_scrap_entries(ids: List[str], user) -> int:
    """Restore archived scrap entries."""
    updated = ScrapEntry.objects.filter(id__in=ids, is_archived=True).update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Restored %s scrap entry(ies) by %s", updated, user)
    return updated


@transaction.atomic
def archive_scrap_types(ids: List[str], user) -> int:
    """Archive scrap types by id."""
    updated = ScrapType.objects.filter(id__in=ids, is_archived=False).update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Archived %s scrap type(s) by %s", updated, user)
    return updated


@transaction.atomic
def restore_scrap_types(ids: List[str], user) -> int:
    """Restore archived scrap types."""
    updated = ScrapType.objects.filter(id__in=ids, is_archived=True).update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Restored %s scrap type(s) by %s", updated, user)
    return updated


@transaction.atomic
def archive_processes(ids: List[str], user) -> int:
    """Archive processes by id."""
    updated = Process.objects.filter(id__in=ids, is_archived=False).update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Archived %s process(es) by %s", updated, user)
    return updated


@transaction.atomic
def restore_processes(ids: List[str], user) -> int:
    """Restore archived processes."""
    updated = Process.objects.filter(id__in=ids, is_archived=True).update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Restored %s process(es) by %s", updated, user)
    return updated
