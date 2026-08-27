"""
Packing / dispatch completion helpers using Work Order tolerance.

Examples (order 500 pcs, tolerance +-10%):
- Max allowed pack/dispatch: 550 pcs
- First bundle (any qty) → packing In-Process (WAITING_FOR_PACKING)
- Packed / Dispatched when cumulative qty reaches order qty (500 pcs / net weight)
"""

from __future__ import annotations

import math
import re
from decimal import Decimal


def parse_tolerance_percent(tolerance) -> Decimal:
    """Extract numeric percent from WO tolerance values like '+-10%', '+5%', 'Zero(0)'."""
    if not tolerance:
        return Decimal("0")
    text = str(tolerance).strip()
    if not text or text.lower().startswith("zero"):
        return Decimal("0")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return Decimal("0")
    try:
        return Decimal(match.group(1))
    except Exception:
        return Decimal("0")


def get_order_tolerance_limits(workorder_detail):
    """
    Return (order_pcs, order_weight, max_pcs, max_weight, percent).
    Max = order * (1 + tolerance%).
    """
    order_pcs = int(workorder_detail.pieces or 0)
    order_weight = Decimal(str(workorder_detail.net_weight or 0))
    wo = getattr(workorder_detail, "workorder", None)
    percent = parse_tolerance_percent(getattr(wo, "tolerance", None) if wo else None)

    extra_pcs = math.ceil(order_pcs * float(percent) / 100) if order_pcs else 0
    max_pcs = order_pcs + extra_pcs
    max_weight = (
        order_weight * (Decimal("1") + (percent / Decimal("100")))
        if order_weight
        else Decimal("0")
    )
    return order_pcs, order_weight, max_pcs, max_weight, percent


def is_quantity_fulfilled(total_pcs, total_weight, workorder_detail) -> bool:
    """
    True when packed/dispatched quantity has met the ordered qty
    (pieces and/or net weight). Tolerance only expands the *allowed max*,
    not the fulfillment threshold.
    """
    order_pcs, order_weight, _, _, _ = get_order_tolerance_limits(workorder_detail)
    pcs = int(total_pcs or 0)
    weight = Decimal(str(total_weight or 0))

    pcs_done = order_pcs > 0 and pcs >= order_pcs
    weight_done = order_weight > 0 and weight >= order_weight
    return pcs_done or weight_done


def is_within_tolerance_max(total_pcs, total_weight, workorder_detail) -> bool:
    """True when totals do not exceed order + tolerance."""
    _, _, max_pcs, max_weight, _ = get_order_tolerance_limits(workorder_detail)
    pcs = int(total_pcs or 0)
    weight = Decimal(str(total_weight or 0))
    if max_pcs and pcs > max_pcs:
        return False
    if max_weight and weight > max_weight:
        return False
    return True
