"""Workorder / item / planning process-tracking stage definitions."""

# Canonical process stages (item + planning tracks).
# Existing WorkOrder.status / WorkOrderDetail.status values are NOT replaced.
PROCESS_STAGE_CHOICES = (
    ("WO_CREATED", "Work Order Created"),
    ("MKT_APPROVED", "Marketing Approved"),
    ("DESIGN_APPROVED", "Design Approved"),
    ("MGMT_APPROVED", "Management Approved"),
    ("OPEN", "Open"),
    ("IN_PLANNING", "Planning"),
    ("IN_PRODUCTION", "Under Production"),
    ("ONLINE_INSPECTION", "Online Inspection"),
    ("DIMENSION_INSPECTION", "Dimension Inspection"),
    ("AGEING", "Ageing"),
    # Always after Dimension Inspection; after Ageing when Ageing applies
    ("MECHANICAL_TEST", "Mechanical Test"),
    # --- Jobwork (Surface Finish driven; shown only when selected) ---
    ("JW_ENGINEERING", "Jobwork — Engineering"),
    ("JW_CUTTING", "Jobwork — Cutting"),
    ("JW_MACHINING", "Jobwork — Machining"),
    ("JW_DEBURRING", "Jobwork — Deburring"),
    ("JW_SURFACE_TREATMENT", "Jobwork — Surface Treatment"),
    ("JW_ANODISING", "Jobwork — Anodising"),
    ("JW_POWDER_COATING", "Jobwork — Powder Coating"),
    ("JW_PVDF", "Jobwork — PVDF"),
    ("JW_LASER_MARKING", "Jobwork — Laser Marking"),
    ("JW_THERMAL_BREAK", "Jobwork — Thermal Break"),
    ("JW_VENDOR_OUT", "Sent to Third Party Vendor"),
    ("JW_INVOICE_LINKED", "Jobwork Invoice Linked"),
    ("JW_RETURN_QC", "Return QC Inspection"),
    # --- Mill-finish / in-house path ---
    ("FINAL_QC", "Final QC"),
    ("WAITING_FOR_PACKING", "Waiting For Packing"),
    ("PACKED", "Packed"),
    ("DISPATCHED", "Dispatched"),
    ("CLOSED", "Closed"),
)

PROCESS_STAGE_LABELS = dict(PROCESS_STAGE_CHOICES)

# Ordered pipeline (sequence index = list index)
PROCESS_STAGE_ORDER = [code for code, _ in PROCESS_STAGE_CHOICES]

# Core stages always considered for planning tracks (jobwork inserted dynamically)
PLANNING_CORE_BEFORE_JOBWORK = [
    "IN_PLANNING",
    "IN_PRODUCTION",
    "ONLINE_INSPECTION",
    "DIMENSION_INSPECTION",
    "AGEING",
    "MECHANICAL_TEST",
]
PLANNING_CORE_AFTER_JOBWORK = [
    "FINAL_QC",
    "WAITING_FOR_PACKING",
    "PACKED",
    "DISPATCHED",
    "CLOSED",
]

# Backward-compatible alias used by older callers
PLANNING_TRACK_STAGES = (
    PLANNING_CORE_BEFORE_JOBWORK
    + [
        "JW_ENGINEERING",
        "JW_CUTTING",
        "JW_MACHINING",
        "JW_DEBURRING",
        "JW_SURFACE_TREATMENT",
        "JW_ANODISING",
        "JW_POWDER_COATING",
        "JW_PVDF",
        "JW_LASER_MARKING",
        "JW_THERMAL_BREAK",
        "JW_VENDOR_OUT",
        "JW_INVOICE_LINKED",
        "JW_RETURN_QC",
    ]
    + PLANNING_CORE_AFTER_JOBWORK
)

JOBWORK_STAGE_CODES = {
    "JW_ENGINEERING",
    "JW_CUTTING",
    "JW_MACHINING",
    "JW_DEBURRING",
    "JW_SURFACE_TREATMENT",
    "JW_ANODISING",
    "JW_POWDER_COATING",
    "JW_PVDF",
    "JW_LASER_MARKING",
    "JW_THERMAL_BREAK",
    "JW_VENDOR_OUT",
    "JW_INVOICE_LINKED",
    "JW_RETURN_QC",
}

# Approval stages are NOT part of the default SO → WO process checklist.
# They appear only when the Work Order is actually in an approval status.
APPROVAL_STAGE_CODES = (
    "MKT_APPROVED",
    "DESIGN_APPROVED",
    "MGMT_APPROVED",
)

# Legacy WO.status → which approval stage(s) to show
APPROVAL_STAGES_BY_WO_STATUS = {
    "App- MKT Dpt": ("MKT_APPROVED",),
    "App- Design Dpt": ("MKT_APPROVED", "DESIGN_APPROVED"),
    "App-Management": ("MKT_APPROVED", "DESIGN_APPROVED", "MGMT_APPROVED"),
}

# "Open" is not default on SO → WO create; only when WO status is Open
OPEN_STAGE_WO_STATUSES = {"Open"}

# Surface Finish master names (jobwork_type.name) that trigger vendor jobwork flow
JOBWORK_SURFACE_FINISH_NAMES = {
    "Engineering",
    "Surface treatment",
    "Laser marking",
    "Thermal Break",
}

# When is each process marked complete?
STAGE_COMPLETION_TRIGGERS = {
    "WO_CREATED": "When Work Order item is created (Sales Order sync / WO create).",
    "MKT_APPROVED": "When Marketing approval is recorded on the Work Order.",
    "DESIGN_APPROVED": "When Design approval is recorded on the Work Order.",
    "MGMT_APPROVED": "When Management approval is recorded on the Work Order.",
    "OPEN": "When Work Order is opened for execution.",
    "IN_PLANNING": "When a Planning entry is created for the item (including single-item planning).",
    "IN_PRODUCTION": "When Production entry is Submitted (final, not Draft).",
    "ONLINE_INSPECTION": "When Online Inspection is recorded against production.",
    "DIMENSION_INSPECTION": "When Dimension Inspection is recorded against production / work order.",
    "AGEING": "When Ageing batch includes this item’s production (only if Ageing Cycle exists for Alloy+Temper).",
    "MECHANICAL_TEST": "When Mechanical Test is recorded (after Ageing if required; otherwise directly after Dimension Inspection).",
    "JW_ENGINEERING": "When Surface Finish includes Engineering (placeholder until Cutting/Machining/Deburring are set).",
    "JW_CUTTING": (
        "When Engineering → Cutting is selected and cutting is completed "
        "(in-house by default; vendor path only if Out Source / other vendor processes apply)."
    ),
    "JW_MACHINING": "When Engineering → Machining is selected and vendor jobwork for machining is done / issued.",
    "JW_DEBURRING": "When Engineering → Deburring is selected and vendor jobwork for deburring is done / issued.",
    "JW_SURFACE_TREATMENT": "When Surface Finish includes Surface treatment (placeholder until Anodising/PC/PVDF are set).",
    "JW_ANODISING": "When Surface treatment → Anodising is selected and vendor jobwork is done / issued.",
    "JW_POWDER_COATING": "When Surface treatment → Powder Coating is selected and vendor jobwork is done / issued.",
    "JW_PVDF": "When Surface treatment → PVDF is selected and vendor jobwork is done / issued.",
    "JW_LASER_MARKING": "When Surface Finish includes Laser marking and vendor jobwork is done / issued.",
    "JW_THERMAL_BREAK": "When Surface Finish includes Thermal Break and vendor jobwork is done / issued.",
    "JW_VENDOR_OUT": (
        "When material is sent to the Third Party Vendor "
        "(only on vendor jobwork path — not for in-house Cutting alone)."
    ),
    "JW_INVOICE_LINKED": (
        "When Jobwork Invoice / Challan is linked for vendor jobwork "
        "(Machining, Anodising, etc.)."
    ),
    "JW_RETURN_QC": (
        "When material returns from vendor and Return QC Inspection "
        "is recorded in the Return QC module."
    ),
    "FINAL_QC": "In-house Final QC before packing (Mill Finish / no vendor jobwork path).",
    "WAITING_FOR_PACKING": (
        "When the first Bundle Inward is created for the item "
        "(packing In-Process)."
    ),
    "PACKED": (
        "When packed pieces/weight reach the Work Order order qty "
        "(packing allowed up to order qty + WO Tolerance %)."
    ),
    "DISPATCHED": (
        "When dispatched pieces/weight reach the Work Order order qty "
        "(dispatch allowed up to order qty + WO Tolerance %)."
    ),
    "CLOSED": "When Work Order is closed.",
}

# Map legacy WorkOrderDetail.status → process stage (for backfill only)
LEGACY_DETAIL_STATUS_TO_PROCESS = {
    "Pending": "WO_CREATED",
    "In-Priority": "OPEN",
    "In-Planning": "IN_PLANNING",
    "In-Production": "IN_PRODUCTION",
    "In-Process": "WAITING_FOR_PACKING",
    "Packed": "PACKED",
    "Dispatched": "DISPATCHED",
}

# Map legacy WorkOrder.status → process stage (for backfill only)
LEGACY_WO_STATUS_TO_PROCESS = {
    "W/o create": "WO_CREATED",
    "App- MKT Dpt": "MKT_APPROVED",
    "App- Design Dpt": "DESIGN_APPROVED",
    "App-Management": "MGMT_APPROVED",
    "Open": "OPEN",
    "Planning": "IN_PLANNING",
    "Under Production- Extru / Insp / Ageing/QC": "IN_PRODUCTION",
    "Wating for packing": "WAITING_FOR_PACKING",
    "Waiting for packing": "WAITING_FOR_PACKING",
    "Packed": "PACKED",
    "Dispatched": "DISPATCHED",
    "Closed": "CLOSED",
}

PROCESS_TO_LEGACY_DETAIL_STATUS = {
    "WO_CREATED": "Pending",
    "MKT_APPROVED": "Pending",
    "DESIGN_APPROVED": "Pending",
    "MGMT_APPROVED": "Pending",
    "OPEN": "Pending",
    "IN_PLANNING": "In-Planning",
    "IN_PRODUCTION": "In-Production",
    "ONLINE_INSPECTION": "In-Production",
    "DIMENSION_INSPECTION": "In-Production",
    "MECHANICAL_TEST": "In-Production",
    "AGEING": "In-Production",
    "JW_ENGINEERING": "In-Process",
    "JW_CUTTING": "In-Process",
    "JW_MACHINING": "In-Process",
    "JW_DEBURRING": "In-Process",
    "JW_SURFACE_TREATMENT": "In-Process",
    "JW_ANODISING": "In-Process",
    "JW_POWDER_COATING": "In-Process",
    "JW_PVDF": "In-Process",
    "JW_LASER_MARKING": "In-Process",
    "JW_THERMAL_BREAK": "In-Process",
    "JW_VENDOR_OUT": "In-Process",
    "JW_INVOICE_LINKED": "In-Process",
    "JW_RETURN_QC": "In-Process",
    "FINAL_QC": "In-Production",
    "WAITING_FOR_PACKING": "In-Process",
    "PACKED": "Packed",
    "DISPATCHED": "Dispatched",
    "CLOSED": "Dispatched",
}
