from enum import Enum


class FileType(Enum):
    CERTIFICATE = "CERTIFICATE"
    DRAWING = "DRAWING"
    PROFILE_PICTURE = "PROFILE_PICTURE"
    DATA_FILE = "DATA_FILE"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.replace("_", " ").title()) for tag in cls]


class QuotationStatusEnum(Enum):
    QUOTATION = "QUOTATION"
    WORKORDER = "WORKORDER"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.replace("_", " ").title()) for tag in cls]


class QuotationRateEnum:
    KG = "KG"
    RMT = "RMT"
    PIECE = "PIECE"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.title()) for tag in cls]


class JobworkEnum:
    MILL_FINISH = "MILL FINISH"
    ENGINEERING = "ENGINEERING"
    SURFACE_TREATMENT = "SURFACE TREATMENT"
    OUT_SOURCE = "OUT SOURCE"
    LASER_MARKING = "LASER MARKING"
    THERMAL_BREACHING = "THERMAL BREACHING"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.replace("_", " ").title()) for tag in cls]


class NalcoRateEnum(Enum):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class WOStatusEnum(Enum):
    WO_CREATE = "W/O CREATE"
    APP_MKT_DPT = "APP- MKT DPT"
    APP_DESIGN_DPT = "APP- DESIGN DPT"
    APP_MANAGEMENT = "APP-MANAGEMENT"
    OPEN = "OPEN"
    PLANNING = "PLANNING"
    UNDER_PRODUCTION = "UNDER PRODUCTION- EXTRU / INSP / AGEING/QC"
    WAITING_FOR_PACKING = "WAITING FOR PACKING"
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    CLOSED = "CLOSED"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class ToleranceEnum(Enum):
    ZERO_0 = "ZERO(0)"
    PLUS_MINUS_3 = "+-3%"
    PLUS_MINUS_5 = "+-5%"
    PLUS_MINUS_7 = "+-7%"
    PLUS_MINUS_10 = "+-10%"
    PLUS_3 = "+3%"
    PLUS_5 = "+5%"
    PLUS_7 = "+7%"
    PLUS_10 = "+10%"
    MINUS_3 = "-3%"
    MINUS_5 = "-5%"
    MINUS_7 = "-7%"
    MINUS_10 = "-10%"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class WorkorderEnum(Enum):
    IN_HOUSE = "IN HOUSE"
    JOB_WORK = "JOB WORK"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class WODetailEnum:
    PACKED = "PACKED"
    PENDING = "PENDING"
    IN_PROCESS = "IN PROCESS"
    DISPATCHED = "DISPATCHED"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


allowed_file_types = {
    "CERTIFICATE": [".pdf", ".jpg", ".jpeg", ".png"],
    "DRAWING": [".pdf", ".jpg", ".jpeg", ".png", ".dwg"],
    "PROFILE_PICTURE": [".jpg", ".jpeg", ".png"],
    "DATA_FILE": [".csv", ".xlsx", ".xls", ".json"],
}


UPLOADING_ALLOWED_MODELS = [
    "alloy",
    "aging_cycle",
    "bundle_inward",
    "bundle_outward",
    "country",
    "currency",
    "die",
    "diecategory",
    "diegroup",
    "diepress",
    "diesubcategory",
    "dietype",
    "quotation",
    "tool",
    "excess_stock",
    "nalcomaster",
    "party",
    "planning",
    "production",
    "proforma",
    "customer",
    "gsttype",
    "country",
    "currency",
    "user",
    "vendor",
    "warehouse",
    "workorder",
]
