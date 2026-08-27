"""
Scrap Generation Remelt service layer.
Business logic and stock movements for remelt transactions.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from product.models import Item
from scrap_entry.models import ScrapStoreStock
from store.models import Store

from scrap_generation_remelt.models import (
    ScrapGenerationRemelt,
    ScrapGenerationRemeltItem,
)

logger = logging.getLogger("file")

REFERENCE_TYPE_SCRAP_GENERATION_REMELT = "SCRAP_GENERATION_REMELT"



def _get_or_create_scrap_stock(store_id: str, item_id: str):
    return ScrapStoreStock.objects.select_for_update().get_or_create(
        store_id=store_id,
        item_id=item_id,
        defaults={"quantity": Decimal("0")},
    )[0]


def _increase_scrap_store_stock(store_id: str, item_id: str, qty: Decimal) -> None:
    stock = _get_or_create_scrap_stock(store_id, item_id)
    stock.quantity += qty
    stock.save(update_fields=["quantity", "updated_at"])


def _validate_store_in_plant(store_id: str, plant_id: str) -> None:
    exists = Store.objects.filter(
        pk=store_id, plant_id=plant_id, deleted=False
    ).exists()
    if not exists:
        raise ValidationError("Store does not belong to selected plant or is inactive.")


def _validate_destination_scrap_store(store_id: str) -> None:
    store = (
        Store.objects.filter(pk=store_id, deleted=False)
        .select_related("store_type")
        .first()
    )
    if not store:
        raise ValidationError("Invalid destination_store.")
    store_type_name = (
        (store.store_type.name if store.store_type else "") or ""
    ).lower()
    if "scrap" not in store_type_name:
        raise ValidationError("destination_store must be a scrap type store.")


def _validate_item_heat_tracking(item: Item, batch_heat: str | None) -> None:
    if getattr(item, "heat_tracking", False) and not (
        batch_heat and str(batch_heat).strip()
    ):
        raise ValidationError(
            f"Item {item.item_code} has heat tracking enabled. batch_heat is mandatory."
        )


@transaction.atomic
def create_scrap_generation_remelt(
    validated_data: Dict[str, Any], user
) -> ScrapGenerationRemelt:
    items_data = validated_data.pop("items", [])
    if not items_data:
        raise ValidationError("At least one item is required.")

    remelt_no = validated_data.get("remelt_no")
    if not remelt_no:
        from utils.generate_number import generate_scrap_generation_remelt_no

        remelt_no = generate_scrap_generation_remelt_no()

    plant_id = validated_data.get("plant")
    source_store_id = validated_data.get("source_store")
    destination_store_id = validated_data.get("destination_store")

    plant_id = str(plant_id.pk) if hasattr(plant_id, "pk") else str(plant_id)
    source_store_id = (
        str(source_store_id.pk)
        if hasattr(source_store_id, "pk")
        else str(source_store_id)
    )
    destination_store_id = (
        str(destination_store_id.pk)
        if hasattr(destination_store_id, "pk")
        else str(destination_store_id)
    )

    if source_store_id == destination_store_id:
        raise ValidationError("source_store and destination_store must be different.")

    _validate_store_in_plant(source_store_id, plant_id)
    _validate_store_in_plant(destination_store_id, plant_id)
    _validate_destination_scrap_store(destination_store_id)

    remelt = ScrapGenerationRemelt.objects.create(
        remelt_no=remelt_no,
        created_by=user,
        updated_by=user,
        status=ScrapGenerationRemelt.STATUS_DRAFT,
        total_qty=Decimal("0"),
        plant_id=plant_id,
        source_store_id=source_store_id,
        destination_store_id=destination_store_id,
        **{
            k: v
            for k, v in validated_data.items()
            if k not in ("plant", "source_store", "destination_store")
        },
    )

    item_objs = []
    for row in items_data:
        qty = Decimal(str(row["qty"]))
        if qty <= 0:
            raise ValidationError("qty must be greater than 0.")
        item = Item.objects.filter(pk=row["item"]).first()
        if not item:
            raise ValidationError(f"Item {row['item']} not found.")
        _validate_item_heat_tracking(item, row.get("batch_heat"))
        item_objs.append(
            ScrapGenerationRemeltItem(
                scrap_generation_remelt=remelt,
                item_id=row["item"],
                batch_heat=row.get("batch_heat"),
                qty=qty,
                uom_id=row["uom"],
                remarks=row.get("remarks"),
            )
        )

    ScrapGenerationRemeltItem.objects.bulk_create(item_objs)
    totals = ScrapGenerationRemeltItem.objects.filter(
        scrap_generation_remelt=remelt
    ).aggregate(
        total_qty=Sum("qty"),
    )
    remelt.total_qty = totals["total_qty"] or Decimal("0")
    remelt.save(update_fields=["total_qty"])
    return remelt


def _sync_items(remelt: ScrapGenerationRemelt, items_data: List[Dict]) -> None:
    if not items_data:
        raise ValidationError("At least one item is required.")

    plant_id = str(remelt.plant_id)
    source_store_id = str(remelt.source_store_id)
    ScrapGenerationRemeltItem.objects.filter(scrap_generation_remelt=remelt).delete()

    item_objs = []
    for row in items_data:
        qty = Decimal(str(row["qty"]))
        if qty <= 0:
            raise ValidationError("qty must be greater than 0.")
        item = Item.objects.filter(pk=row["item"]).first()
        if not item:
            raise ValidationError(f"Item {row['item']} not found.")
        _validate_item_heat_tracking(item, row.get("batch_heat"))
        item_objs.append(
            ScrapGenerationRemeltItem(
                scrap_generation_remelt=remelt,
                item_id=row["item"],
                batch_heat=row.get("batch_heat"),
                qty=qty,
                uom_id=row["uom"],
                remarks=row.get("remarks"),
            )
        )

    ScrapGenerationRemeltItem.objects.bulk_create(item_objs)


@transaction.atomic
def update_scrap_generation_remelt(
    instance: ScrapGenerationRemelt, validated_data: Dict[str, Any], user
) -> ScrapGenerationRemelt:
    if instance.status != ScrapGenerationRemelt.STATUS_DRAFT:
        raise ValidationError("Only DRAFT records can be edited.")

    items_data = validated_data.pop("items", None)
    for attr, value in validated_data.items():
        if attr != "items" and hasattr(instance, attr):
            setattr(instance, attr, value)

    if instance.source_store_id == instance.destination_store_id:
        raise ValidationError("source_store and destination_store must be different.")
    _validate_store_in_plant(str(instance.source_store_id), str(instance.plant_id))
    _validate_store_in_plant(str(instance.destination_store_id), str(instance.plant_id))
    _validate_destination_scrap_store(str(instance.destination_store_id))

    instance.updated_by = user
    instance.updated_at = timezone.now()
    update_fields = [k for k in validated_data if k != "items"] + [
        "updated_by",
        "updated_at",
    ]
    instance.save(update_fields=list(set(update_fields)))

    if items_data is not None:
        _sync_items(instance, items_data)

    totals = ScrapGenerationRemeltItem.objects.filter(
        scrap_generation_remelt=instance
    ).aggregate(
        total_qty=Sum("qty"),
    )
    instance.total_qty = totals["total_qty"] or Decimal("0")
    instance.save(update_fields=["total_qty"])
    return instance


def submit_scrap_generation_remelt(
    remelt: ScrapGenerationRemelt, user
) -> ScrapGenerationRemelt:
    remelt.refresh_from_db()
    if remelt.status != ScrapGenerationRemelt.STATUS_DRAFT:
        raise ValidationError("Only DRAFT records can be submitted.")

    items = list(
        ScrapGenerationRemeltItem.objects.filter(
            scrap_generation_remelt=remelt
        ).select_related("item", "uom")
    )
    if not items:
        raise ValidationError("Cannot submit without at least one item.")

    remelt.status = ScrapGenerationRemelt.STATUS_SUBMITTED
    remelt.updated_by = user
    remelt.updated_at = timezone.now()
    remelt.save(update_fields=["status", "updated_by", "updated_at"])
    return remelt


@transaction.atomic
def complete_scrap_generation_remelt(
    remelt: ScrapGenerationRemelt, user
) -> ScrapGenerationRemelt:
    remelt.refresh_from_db()
    if remelt.status != ScrapGenerationRemelt.STATUS_SUBMITTED:
        raise ValidationError("Only SUBMITTED records can be completed.")

    items = list(
        ScrapGenerationRemeltItem.objects.filter(
            scrap_generation_remelt=remelt
        ).select_related("item", "uom")
    )
    if not items:
        raise ValidationError("Cannot complete without at least one item.")

    remelt.total_qty = sum(i.qty for i in items)
    remelt.status = ScrapGenerationRemelt.STATUS_COMPLETED
    remelt.updated_by = user
    remelt.updated_at = timezone.now()
    remelt.save(update_fields=["total_qty", "status", "updated_by", "updated_at"])
    return remelt


def cancel_submit(remelt: ScrapGenerationRemelt, user) -> ScrapGenerationRemelt:
    remelt.refresh_from_db()
    if remelt.status == ScrapGenerationRemelt.STATUS_COMPLETED:
        raise ValidationError("COMPLETED records cannot be cancelled.")
    if remelt.status != ScrapGenerationRemelt.STATUS_SUBMITTED:
        raise ValidationError("Only SUBMITTED records can be cancelled.")

    remelt.status = ScrapGenerationRemelt.STATUS_DRAFT
    remelt.updated_by = user
    remelt.updated_at = timezone.now()
    remelt.save(update_fields=["status", "updated_by", "updated_at"])
    return remelt


@transaction.atomic
def archive_scrap_generation_remelts(ids: List[str], user) -> int:
    qs = ScrapGenerationRemelt.objects.filter(id__in=ids, is_archived=False)
    non_draft = qs.exclude(status=ScrapGenerationRemelt.STATUS_DRAFT).first()
    if non_draft:
        raise ValidationError(
            f"Cannot archive record {non_draft.remelt_no}. Only DRAFT records can be archived."
        )
    return qs.filter(status=ScrapGenerationRemelt.STATUS_DRAFT).update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )


@transaction.atomic
def restore_scrap_generation_remelts(ids: List[str], user) -> int:
    return ScrapGenerationRemelt.objects.filter(id__in=ids, is_archived=True).update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
