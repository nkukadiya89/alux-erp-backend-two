from decimal import Decimal
from types import SimpleNamespace

from utils.packing_tolerance import (
    get_order_tolerance_limits,
    is_quantity_fulfilled,
    parse_tolerance_percent,
)


def test_parse_tolerance_percent():
    assert parse_tolerance_percent("Zero(0)") == Decimal("0")
    assert parse_tolerance_percent("+-10%") == Decimal("10")
    assert parse_tolerance_percent("+5%") == Decimal("5")
    assert parse_tolerance_percent(None) == Decimal("0")


def test_limits_and_fulfillment_500_with_10_percent():
    wo = SimpleNamespace(tolerance="+-10%")
    detail = SimpleNamespace(pieces=500, net_weight=Decimal("3134.9"), workorder=wo)

    order_pcs, order_wt, max_pcs, max_wt, percent = get_order_tolerance_limits(detail)
    assert order_pcs == 500
    assert max_pcs == 550
    assert percent == Decimal("10")
    assert max_wt == order_wt * Decimal("1.10")

    assert is_quantity_fulfilled(10, Decimal("50"), detail) is False
    assert is_quantity_fulfilled(500, Decimal("3134.9"), detail) is True
    assert is_quantity_fulfilled(550, Decimal("3200"), detail) is True
