"""
Scrap Sale service layer.
Business logic and atomic transactions for create, update, finalize, cancel, archive.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

from scrap_sale.models import ScrapSale, ScrapSaleItem, ScrapItem, ScrapStock

logger = logging.getLogger("file")


def _get_available_qty(scrap_item_id) -> Decimal:
    """Return current scrap stock quantity for the scrap item."""
    try:
        stock = ScrapStock.objects.get(scrap_item_id=scrap_item_id)
        return stock.quantity
    except ScrapStock.DoesNotExist:
        return Decimal("0")


def _reduce_scrap_stock(scrap_item_id: str, qty: Decimal) -> None:
    """Reduce scrap store stock by qty. Caller must run inside transaction."""
    stock = ScrapStock.objects.select_for_update().get(scrap_item_id=scrap_item_id)
    if stock.quantity < qty:
        raise ValidationError(
            f"Insufficient scrap stock for item {stock.scrap_item.item_code}. "
            f"Available: {stock.quantity}, requested: {qty}."
        )
    stock.quantity -= qty
    stock.save(update_fields=["quantity", "updated_at"])


def _create_inventory_ledger_entry(scrap_sale: ScrapSale, user) -> None:
    """
    Create inventory ledger entry for scrap sale (stock reduction).
    Hook for ledger module integration; no-op if ledger not present.
    """
    try:
        # Placeholder: integrate with inventory/ledger app when available
        logger.info(
            "Scrap sale ledger hook: sale_no=%s total_qty=%s",
            scrap_sale.sale_no,
            scrap_sale.total_qty,
        )
    except Exception as e:
        logger.warning("Scrap sale ledger hook failed (non-blocking): %s", e)


def _create_financial_journal_entry(scrap_sale: ScrapSale, user) -> None:
    """
    Create financial journal entry for scrap sale.
    Hook for finance module integration; no-op if journal not present.
    """
    try:
        logger.info(
            "Scrap sale journal hook: sale_no=%s total_value=%s",
            scrap_sale.sale_no,
            scrap_sale.total_value,
        )
    except Exception as e:
        logger.warning("Scrap sale journal hook failed (non-blocking): %s", e)


@transaction.atomic
def create_scrap_sale(validated_data: Dict[str, Any], user) -> ScrapSale:
    """Create ScrapSale and items. Validates at least one item and sale_qty <= available."""
    items_data = validated_data.pop("items", [])

    if not items_data:
        raise ValidationError("At least one item is required.")

    sale_no = validated_data.get("sale_no")
    if not sale_no:
        from utils.generate_number import generate_scrap_sale_no

        sale_no = generate_scrap_sale_no()

    scrap_sale = ScrapSale.objects.create(
        sale_no=sale_no,
        created_by=user,
        updated_by=user,
        status=ScrapSale.STATUS_DRAFT,
        total_qty=Decimal("0"),
        total_value=Decimal("0"),
        **validated_data,
    )

    item_objs = []
    for row in items_data:
        sale_qty = Decimal(str(row["sale_qty"]))
        if sale_qty <= 0:
            raise ValidationError("sale_qty must be greater than 0.")
        available = _get_available_qty(row["scrap_item"])
        if sale_qty > available:
            scrap_item = ScrapItem.objects.get(pk=row["scrap_item"])
            raise ValidationError(
                f"sale_qty for {scrap_item.item_code} exceeds available stock ({available})."
            )
        rate = Decimal(str(row.get("rate", 0)))
        total_value = (sale_qty * rate).quantize(Decimal("0.01"))
        item_objs.append(
            ScrapSaleItem(
                scrap_sale=scrap_sale,
                scrap_item_id=row["scrap_item"],
                sale_qty=sale_qty,
                uom_id=row["uom"],
                rate=rate,
                total_value=total_value,
                remarks=row.get("remarks"),
            )
        )

    ScrapSaleItem.objects.bulk_create(item_objs)

    # Recompute header totals
    totals = ScrapSaleItem.objects.filter(scrap_sale=scrap_sale).aggregate(
        total_qty=Sum("sale_qty"),
        total_value=Sum("total_value"),
    )
    scrap_sale.total_qty = totals["total_qty"] or Decimal("0")
    scrap_sale.total_value = totals["total_value"] or Decimal("0")
    scrap_sale.save(update_fields=["total_qty", "total_value"])

    logger.info("Created scrap sale %s by %s", scrap_sale.sale_no, user)
    return scrap_sale


def _sync_items(scrap_sale: ScrapSale, items_data: List[Dict], user) -> None:
    """Replace sale items with new set. Validates sale_qty and availability for DRAFT."""
    if not items_data:
        raise ValidationError("At least one item is required.")

    ScrapSaleItem.objects.filter(scrap_sale=scrap_sale).delete()

    item_objs = []
    for row in items_data:
        sale_qty = Decimal(str(row["sale_qty"]))
        if sale_qty <= 0:
            raise ValidationError("sale_qty must be greater than 0.")
        available = _get_available_qty(row["scrap_item"])
        if sale_qty > available:
            scrap_item = ScrapItem.objects.get(pk=row["scrap_item"])
            raise ValidationError(
                f"sale_qty for {scrap_item.item_code} exceeds available stock ({available})."
            )
        rate = Decimal(str(row.get("rate", 0)))
        total_value = (sale_qty * rate).quantize(Decimal("0.01"))
        item_objs.append(
            ScrapSaleItem(
                scrap_sale=scrap_sale,
                scrap_item_id=row["scrap_item"],
                sale_qty=sale_qty,
                uom_id=row["uom"],
                rate=rate,
                total_value=total_value,
                remarks=row.get("remarks"),
            )
        )

    ScrapSaleItem.objects.bulk_create(item_objs)


@transaction.atomic
def update_scrap_sale(
    instance: ScrapSale, validated_data: Dict[str, Any], user
) -> ScrapSale:
    """Update ScrapSale and items. Only DRAFT can be edited."""
    if instance.status != ScrapSale.STATUS_DRAFT:
        raise ValidationError("Only DRAFT scrap sales can be edited.")

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

    # Recompute totals
    totals = ScrapSaleItem.objects.filter(scrap_sale=instance).aggregate(
        total_qty=Sum("sale_qty"),
        total_value=Sum("total_value"),
    )
    instance.total_qty = totals["total_qty"] or Decimal("0")
    instance.total_value = totals["total_value"] or Decimal("0")
    instance.save(update_fields=["total_qty", "total_value"])

    logger.info("Updated scrap sale %s by %s", instance.sale_no, user)
    return instance


@transaction.atomic
def finalize_scrap_sale(scrap_sale: ScrapSale, user) -> ScrapSale:
    """
    Finalize scrap sale: validate stock, reduce scrap store, ledger + journal hooks, set status.
    """
    scrap_sale.refresh_from_db()

    if scrap_sale.status != ScrapSale.STATUS_DRAFT:
        raise ValidationError("Only DRAFT scrap sales can be finalized.")

    items = list(
        ScrapSaleItem.objects.filter(scrap_sale=scrap_sale).select_related("scrap_item")
    )
    if not items:
        raise ValidationError("Cannot finalize without at least one item.")

    # 1. Validate stock availability
    for item in items:
        available = _get_available_qty(item.scrap_item_id)
        if item.sale_qty > available:
            raise ValidationError(
                f"Insufficient scrap stock for {item.scrap_item.item_code}. "
                f"Available: {available}, requested: {item.sale_qty}."
            )

    # 2. Reduce scrap store stock
    for item in items:
        _reduce_scrap_stock(item.scrap_item_id, item.sale_qty)

    # 3. Create inventory ledger entry (hook)
    _create_inventory_ledger_entry(scrap_sale, user)

    # 4. Create financial journal entry (hook)
    _create_financial_journal_entry(scrap_sale, user)

    # 5. Compute and update totals
    total_qty = sum(i.sale_qty for i in items)
    total_value = sum(i.total_value for i in items)
    scrap_sale.total_qty = total_qty
    scrap_sale.total_value = total_value
    scrap_sale.status = ScrapSale.STATUS_FINALIZED
    scrap_sale.updated_by = user
    scrap_sale.updated_at = timezone.now()
    scrap_sale.save(
        update_fields=["total_qty", "total_value", "status", "updated_by", "updated_at"]
    )

    logger.info("Finalized scrap sale %s by %s", scrap_sale.sale_no, user)
    return scrap_sale


def cancel_scrap_sale(scrap_sale: ScrapSale, user) -> ScrapSale:
    """Cancel scrap sale. Only DRAFT can be cancelled; FINALIZED must use reversal flow."""
    scrap_sale.refresh_from_db()

    if scrap_sale.status == ScrapSale.STATUS_FINALIZED:
        raise ValidationError(
            "FINALIZED scrap sales cannot be cancelled. Use reversal entry module instead."
        )
    if scrap_sale.status == ScrapSale.STATUS_CANCELLED:
        raise ValidationError("Scrap sale is already cancelled.")

    scrap_sale.status = ScrapSale.STATUS_CANCELLED
    scrap_sale.updated_by = user
    scrap_sale.updated_at = timezone.now()
    scrap_sale.save(update_fields=["status", "updated_by", "updated_at"])

    logger.info("Cancelled scrap sale %s by %s", scrap_sale.sale_no, user)
    return scrap_sale


@transaction.atomic
def archive_scrap_sales(ids: List[str], user) -> int:
    """Archive scrap sales. Allowed only for DRAFT and CANCELLED."""
    qs = ScrapSale.objects.filter(id__in=ids, is_archived=False)
    finalized = qs.filter(status=ScrapSale.STATUS_FINALIZED).first()
    if finalized:
        raise ValidationError(
            f"Cannot archive FINALIZED scrap sale {finalized.sale_no}. "
            "Only DRAFT and CANCELLED can be archived."
        )
    updated = qs.filter(
        status__in=[ScrapSale.STATUS_DRAFT, ScrapSale.STATUS_CANCELLED]
    ).update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Archived %s scrap sale(s) by %s", updated, user)
    return updated


@transaction.atomic
def restore_scrap_sales(ids: List[str], user) -> int:
    """Restore archived scrap sales."""
    updated = ScrapSale.objects.filter(id__in=ids, is_archived=True).update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Restored %s scrap sale(s) by %s", updated, user)
    return updated


def get_available_scrap_items_for_sale():
    """
    Return scrap items with current available qty for dropdown / available-for-sale API.
    Excludes archived scrap items.
    """
    items = (
        ScrapItem.objects.filter(is_archived=False)
        .select_related("uom")
        .order_by("item_code")
    )
    result = []
    for item in items:
        qty = _get_available_qty(item.id)
        result.append(
            {
                "id": str(item.id),
                "item_code": item.item_code,
                "item_name": item.item_name,
                "uom_id": str(item.uom_id),
                "uom_code": item.uom.uom_code if item.uom else None,
                "available_qty": str(qty),
            }
        )
    return result
