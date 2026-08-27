"""Unit tests for in-house vs vendor jobwork process stage resolution."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from workorder.process_tracking import (
    requires_vendor_jobwork_path,
    resolve_jobwork_stage_codes,
)


def _detail(names, **flags):
    """Build a light-weight WorkOrderDetail stand-in."""
    qs = MagicMock()
    qs.values_list.return_value = list(names)
    detail = SimpleNamespace(
        surface_finish=qs,
        out_source=False,
        cutting=False,
        machining=False,
        deburring=False,
        anodising=False,
        powder_coating=False,
        pvdf=False,
    )
    for key, value in flags.items():
        setattr(detail, key, value)
    return detail


def test_inhouse_engineering_cutting_only():
    detail = _detail(["Engineering"], cutting=True)
    assert requires_vendor_jobwork_path(detail) is False
    assert resolve_jobwork_stage_codes(detail) == ["JW_CUTTING"]


def test_outsourced_cutting_includes_vendor_path():
    detail = _detail(["Engineering"], cutting=True, out_source=True)
    assert requires_vendor_jobwork_path(detail) is True
    assert resolve_jobwork_stage_codes(detail) == [
        "JW_CUTTING",
        "JW_VENDOR_OUT",
        "JW_INVOICE_LINKED",
        "JW_RETURN_QC",
    ]


def test_vendor_machining_and_anodising():
    detail = _detail(
        ["Engineering", "Surface treatment"],
        machining=True,
        anodising=True,
    )
    assert requires_vendor_jobwork_path(detail) is True
    assert resolve_jobwork_stage_codes(detail) == [
        "JW_MACHINING",
        "JW_ANODISING",
        "JW_VENDOR_OUT",
        "JW_INVOICE_LINKED",
        "JW_RETURN_QC",
    ]


def test_mixed_inhouse_cutting_plus_vendor_machining_anodising():
    detail = _detail(
        ["Engineering", "Surface treatment"],
        cutting=True,
        machining=True,
        anodising=True,
    )
    assert requires_vendor_jobwork_path(detail) is True
    assert resolve_jobwork_stage_codes(detail) == [
        "JW_CUTTING",
        "JW_MACHINING",
        "JW_ANODISING",
        "JW_VENDOR_OUT",
        "JW_INVOICE_LINKED",
        "JW_RETURN_QC",
    ]


def test_mill_finish_no_jobwork_stages():
    detail = _detail(["Mill Finish"])
    assert resolve_jobwork_stage_codes(detail) == []
