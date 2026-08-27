from datetime import date
from django.apps import apps 
from django.db.models import Max
from django.utils import timezone
from django.db import models

from bundle_inward.models import BundleInward
from bundle_outward.models import BundleOutward
from common.models import FinancialYearModel
from customer.models import Customer
from die_quotation.models import DieQuotation
from dietool_production.models import DieTrialLog, DieNitridingBatch
from inquiry.models import Inquiry
from inquiry_quotation.models import InquiryQuotation
from inquiry_salesorder.models import InquirySalesOrder
from planning.models import Planning
from production.models import Production
from proforma.models import Proforma
from quotation.models import Quotation
from warehouse.models import Warehouse
from workorder.models import WorkOrder
from purchase_order.models import PurchaseOrder
from receipt_notes.models import GoodsReceiptNoteDetail
from receipt_notes.models import GoodsReceiptNote
from ageing_cycle.models import AgingCycle

def generate_aging_cycle_no():
    from ageing_cycle.models import AgingCycle

    fy = get_financial_year()
    prefix = f"AC/{fy}/"

    last_cycle_code = (
        AgingCycle.objects.filter(cycle_code__startswith=prefix)
        .order_by("-cycle_code")
        .first()
    )

    if last_cycle_code:
        last_number = int(last_cycle_code.cycle_code.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_failure_no():
    from dietool_production.models import DieFailureLog

    fy = get_financial_year()
    prefix = f"DF/{fy}/"

    last_failure_no = (
        DieFailureLog.objects.filter(failure_no__startswith=prefix)
        .order_by("-failure_no")
        .first()
    )

    if last_failure_no:
        last_number = int(last_failure_no.failure_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"

def generate_return_qc_no():
    from return_qc.models import ReturnQC

    fy = get_financial_year()
    prefix = f"RQC/{fy}/"

    last_doc = (
        ReturnQC.objects.filter(inspection_no__startswith=prefix)
        .order_by("-inspection_no")
        .first()
    )

    if last_doc:
        last_number = int(last_doc.inspection_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_jobwork_challan_no():
    from jobwork_invoice.models import JobworkInvoice

    fy = get_financial_year()
    prefix = f"JW/{fy}/"

    last_challan = (
        JobworkInvoice.objects.filter(challan_no__startswith=prefix)
        .order_by("-challan_no")
        .first()
    )

    if last_challan:
        last_number = int(last_challan.challan_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_ageing_batch_no():
    from aging.models import AgeingBatch

    fy = get_financial_year()
    prefix = f"AGE/{fy}/"

    last_requisition = (
        AgeingBatch.objects.filter(batch_no__startswith=prefix)
        .order_by("-batch_no")
        .first()
    )

    if last_requisition:
        last_number = int(last_requisition.batch_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_material_request_no():
    from material_request.models import MaterialRequest
    fy = get_financial_year()
    prefix = f"MR/{fy}/"

    last_request = (
        MaterialRequest.objects.filter(request_no__startswith=prefix)
        .order_by("-request_no")
        .first()
    )

    if last_request:
        last_number = int(last_request.request_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_material_indent_no():
    MaterialIndent = apps.get_model('material_indent', 'MaterialIndent')

    fy = get_financial_year()
    prefix = f"MI/{fy}/"

    last_request = (
        MaterialIndent.objects.filter(indent_no__startswith=prefix)
        .order_by("-indent_no")
        .first()
    )

    if last_request:
        last_number = int(last_request.indent_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"

def generate_po_no():
    fy = get_financial_year()
    prefix = f"PO/{fy}/"

    last_request = (
         PurchaseOrder.objects.filter(po_no__startswith=prefix)
        .order_by("-po_no")
        .first()
    )

    if last_request:
        last_number = int(last_request.po_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_quality_inspection_no():
    from quality_inspection.models import QualityInspection

    fy = get_financial_year()
    prefix = f"QI/{fy}/"

    last_record = (
        QualityInspection.objects.filter(inspection_no__startswith=prefix)
        .order_by("-inspection_no")
        .first()
    )

    if last_record:
        last_number = int(last_record.inspection_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_grn_request_no():
    fy = get_financial_year()
    prefix = f"GRN/{fy}/"

    last_request = (
        GoodsReceiptNote.objects.filter(grn_no__startswith=prefix)
        .order_by("-grn_no")
        .first()
    )

    if last_request:
        last_number = int(last_request.grn_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_quotation_no(self):
    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(), end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    last_quotation = (
        Quotation.objects.filter(quotation_no__startswith=financial_year_str)
        .order_by("-id")
        .first()
    )

    if last_quotation and last_quotation.quotation_no:
        last_year_str = last_quotation.quotation_no.split("/")[0]

        if last_year_str == financial_year_str:
            last_quotation_no = int(last_quotation.quotation_no.split("/")[-1])
            new_quotation_no = last_quotation_no + 1
        else:
            new_quotation_no = 1
    else:
        new_quotation_no = 1

    formatted_quotation_no = f"{financial_year_str}/{new_quotation_no:04d}"

    return formatted_quotation_no


def generate_order_no(self):
    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(), end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    last_order = (
        WorkOrder.objects.filter(order_no__startswith=financial_year_str)
        .order_by("-id")
        .first()
    )

    if last_order and last_order.order_no:
        last_year_str = last_order.order_no.split("/")[0]

        if last_year_str == financial_year_str:
            last_order_no = int(last_order.order_no.split("/")[-1])
            new_order_no = last_order_no + 1
        else:
            new_order_no = 1
    else:
        new_order_no = 1
    formatted_order_no = f"{financial_year_str}/{new_order_no:04d}"

    return formatted_order_no


def generate_proforma_no(self):
    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(), end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    last_proforma = (
        Proforma.objects.filter(proforma_no__startswith=f"PI/{financial_year_str}")
        .order_by("-id")
        .first()
    )

    if last_proforma and last_proforma.proforma_no:
        last_year_str = last_proforma.proforma_no.split("/")[1]

        if last_year_str == financial_year_str:
            last_proforma_no = int(last_proforma.proforma_no.split("/")[-1])
            new_proforma_no = last_proforma_no + 1
        else:
            new_proforma_no = 1
    else:
        new_proforma_no = 1
    formatted_proforma_no = f"PI/{financial_year_str}/{new_proforma_no:04d}"

    return formatted_proforma_no


def generate_die_quotation_no(self):
    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(), end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    last_die_quotation = (
        DieQuotation.objects.filter(
            die_quotation_no__startswith=f"D/QTN/{financial_year_str}"
        )
        .order_by("-id")
        .first()
    )
    if last_die_quotation and last_die_quotation.die_quotation_no:
        last_year_str = last_die_quotation.die_quotation_no.split("/")[2]

        if last_year_str == financial_year_str:
            last_die_quotation_no = int(
                last_die_quotation.die_quotation_no.split("/")[-1]
            )
            new_die_quotation_no = last_die_quotation_no + 1
        else:
            new_die_quotation_no = 1
    else:
        new_die_quotation_no = 1

    formatted_die_quotation_no = (
        f"D/QTN/{financial_year_str}/{new_die_quotation_no:04d}"
    )

    return formatted_die_quotation_no


def extract_inquiry_base_number(inquiry_base_number):
    if not inquiry_base_number:
        return None
    return inquiry_base_number.zfill(5)


def generate_die_inquiry_number(base_number, index):
    if not base_number or not isinstance(index, int):
        return None
    return f"{base_number}-{index}"


class BundleNumberGenerator:
    def generate_bundle_no(self):
        financial_year = FinancialYearModel.objects.filter(
            start_date__lte=date.today(), end_date__gte=date.today()
        ).first()

        if financial_year:
            year_start = str(financial_year.start_date.year)[-2:]
            year_end = str(financial_year.end_date.year)[-2:]
            financial_year_str = f"{year_start}-{year_end}"
        else:
            financial_year_str = "00-00"

        last_bundle = BundleInward.objects.order_by("-id").first()

        if last_bundle and last_bundle.bundle_no:
            try:
                last_year, last_number = last_bundle.bundle_no.split("/")
                last_number = int(last_number)

                if last_year == financial_year_str:
                    new_bundle_no = last_number + 1
                else:
                    new_bundle_no = 1
            except ValueError:
                new_bundle_no = 1
        else:
            new_bundle_no = 1

        formatted_bundle_no = f"{financial_year_str}/{new_bundle_no:04d}"
        return formatted_bundle_no


def generate_planning_no(self):
    last_planning = Planning.objects.order_by("-id").first()

    if last_planning and last_planning.planning_no:
        last_planning_no = last_planning.planning_no.split("-")[-1]
        last_planning_no = int(last_planning_no)
        new_planning_no = last_planning_no + 1
    else:
        new_planning_no = 1

    formatted_planning_no = f"P-{new_planning_no:04d}"
    return formatted_planning_no


from datetime import date


def get_financial_year():
    today = date.today()
    year = today.year
    if today.month >= 4:
        return f"{str(year)[2:]}-{str(year+1)[2:]}"
    else:
        return f"{str(year-1)[2:]}-{str(year)[2:]}"


def generate_die_requisition_no():
    from die_requisition.models import DieRequisition

    fy = get_financial_year()
    prefix = f"DR/{fy}/"

    last_requisition = (
        DieRequisition.objects.filter(requisition_no__startswith=prefix)
        .order_by("-requisition_no")
        .first()
    )

    if last_requisition:
        last_number = int(last_requisition.requisition_no.split("/")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_correction_request_no():
    from dietool_production.models import CorrectionHistory 

    fy = get_financial_year()
    prefix = f"CR/{fy}/"

    last_record = (
        CorrectionHistory.objects.filter(correction_request_no__startswith=prefix)
        .order_by("-correction_request_no")
        .first()
    )

    if last_record and last_record.correction_request_no:
        try:
            last_number = int(last_record.correction_request_no.split("/")[-1])
            new_number = last_number + 1
        except ValueError:
            new_number = 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_trial_no(): 
    fy = get_financial_year()
    prefix = f"TR/{fy}/"

    last_record = (
        DieTrialLog.objects.filter(trial_no__startswith=prefix)
        .order_by("-trial_no")
        .first()
    )

    if last_record and last_record.trial_no:
        try:
            last_number = int(last_record.trial_no.split("/")[-1])
            new_number = last_number + 1
        except ValueError:
            new_number = 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


def generate_nitriding_batch_no():
    fy = get_financial_year()
    prefix = f"NB/{fy}/"

    last_record = (
        DieNitridingBatch.objects.filter(batch_no__startswith=prefix)
        .order_by("-batch_no")
        .first()
    )

    if last_record and last_record.batch_no:
        try:
            last_number = int(last_record.batch_no.split("/")[-1])
            new_number = last_number + 1
        except ValueError:
            new_number = 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"

def generate_slip_no(self):
    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(),
        end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    last_slip = BundleOutward.objects.order_by("-id").first()

    if last_slip and last_slip.slip_no:
        try:
            last_year, last_number = last_slip.slip_no.split("/")
            last_number = int(last_number)

            if last_year == financial_year_str:
                new_slip_no = last_number + 1
            else:
                new_slip_no = 1
        except ValueError:
            new_slip_no = 1
    else:
        new_slip_no = 1

    formatted_slip_no = f"{financial_year_str}/{new_slip_no:04d}"
    return formatted_slip_no


def generate_warehouse_slip_no():
    current_year = date.today().year
    prefix = str(current_year)

    latest_slip = (
        Warehouse.objects.filter(slip_no__startswith=prefix).aggregate(
            max_slip=Max("slip_no")
        )
    )["max_slip"]

    if latest_slip:
        try:
            last_slip_no = int(latest_slip.split("/")[-1])
            new_slip_no = last_slip_no + 1
        except (ValueError, IndexError):
            new_slip_no = 1
    else:
        new_slip_no = 1
    return f"{prefix}/{new_slip_no:04d}"


def generate_customer_number():
    prefix = "CUS"

    latest_customer = (
        Customer.objects.filter(customer_number__startswith=prefix).aggregate(
            max_number=Max("customer_number")
        )
    )["max_number"]

    if latest_customer:
        try:
            last_number = int(latest_customer.split("-")[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    return f"{prefix}-{new_number:0{max(4, len(str(new_number)))}d}"


def generate_production_number():
    prefix = "PROD"
    current_year = timezone.now().year
    latest_production_no = (
        Production.objects.filter(
            production_no__startswith=f"{prefix}-{current_year}"
        ).aggregate(max_number=Max("production_no"))
    )["max_number"]

    if latest_production_no:
        try:
            last_seq = int(latest_production_no.split("-")[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}-{current_year}-{new_seq:04d}"


def generate_inquiry_number():
    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(), end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    last_inquiry = (
        Inquiry.objects.filter(inquiry_number__startswith=f"INQ/{financial_year_str}")
        .order_by("-id")
        .first()
    )

    if last_inquiry and last_inquiry.inquiry_number:
        parts = last_inquiry.inquiry_number.split("/")
        last_year_str = parts[1] if len(parts) > 1 else ""

        if last_year_str == financial_year_str:
            last_inquiry_no = int(parts[-1])

            new_inquiry_no = last_inquiry_no + 1
        else:
            new_inquiry_no = 1
    else:
        new_inquiry_no = 1

    formatted_inquiry_no = f"INQ/{financial_year_str}/{new_inquiry_no:04d}"
    return formatted_inquiry_no


def generate_inquiry_quotation_number():
    from django.db import transaction

    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(),
        end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    with transaction.atomic():
        quotations = (
            InquiryQuotation.objects.select_for_update()
            .filter(
                quotation_no__startswith=financial_year_str
            )
            .values_list("quotation_no", flat=True)
        )

        max_number = 0

        for quotation_no in quotations:
            try:
                parts = quotation_no.split("/")
                number = int(parts[1])

                if number > max_number:
                    max_number = number

            except (IndexError, ValueError):
                continue

        new_quotation_no = max_number + 1

        return f"{financial_year_str}/{new_quotation_no:04d}"


def generate_gate_entry_no():
    """
    Generate a sequential gate entry number per calendar year.

    Format: GE-YYYY-XXXX
    """
    from datetime import date 
    from gate_entry.models import GateEntry

    current_year = date.today().year
    prefix = f"GE-{current_year}-"

    last_ge = (
        GateEntry.objects.filter(gate_entry_no__startswith=prefix)
        .order_by("-gate_entry_no")
        .values_list("gate_entry_no", flat=True)
        .first()
    )

    if last_ge:
        try:
            seq = int(last_ge.split("-")[-1])
            new_seq = seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"



def generate_gate_pass_no():
    """
    Generate a sequential gate pass number per calendar year.

    Format: GP-YYYY-XXXX
    """
    from gate_pass.models import GatePass

    current_year = date.today().year
    prefix = f"GP-{current_year}-"

    last_gp = (
        GatePass.objects.filter(gate_pass_no__startswith=prefix)
        .order_by("-gate_pass_no")
        .values_list("gate_pass_no", flat=True)
        .first()
    )

    if last_gp:
        try:
            seq = int(last_gp.split("-")[-1])
            new_seq = seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"


def generate_scrap_sale_no():
    """
    Generate a sequential scrap sale number per calendar year.
    Format: SS-YYYY-XXXX
    """
    from scrap_sale.models import ScrapSale

    current_year = date.today().year
    prefix = f"SS-{current_year}-"

    last_ss = (
        ScrapSale.objects.filter(sale_no__startswith=prefix)
        .order_by("-sale_no")
        .values_list("sale_no", flat=True)
        .first()
    )

    if last_ss:
        try:
            seq = int(last_ss.split("-")[-1])
            new_seq = seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"


def generate_scrap_entry_no():
    """
    Generate a sequential scrap entry number per calendar year.
    Format: SE-YYYY-XXXX
    """
    from scrap_entry.models import ScrapEntry

    current_year = date.today().year
    prefix = f"SE-{current_year}-"

    last_se = (
        ScrapEntry.objects.filter(entry_no__startswith=prefix)
        .order_by("-entry_no")
        .values_list("entry_no", flat=True)
        .first()
    )

    if last_se:
        try:
            seq = int(last_se.split("-")[-1])
            new_seq = seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"


def generate_scrap_transfer_no():
    """
    Generate a sequential scrap transfer number per calendar year.
    Format: ST-YYYY-XXXX
    """
    from scrap_transfer.models import ScrapTransfer

    current_year = date.today().year
    prefix = f"ST-{current_year}-"

    last_st = (
        ScrapTransfer.objects.filter(transfer_no__startswith=prefix)
        .order_by("-transfer_no")
        .values_list("transfer_no", flat=True)
        .first()
    )

    if last_st:
        try:
            seq = int(last_st.split("-")[-1])
            new_seq = seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"


def generate_scrap_generation_remelt_no():
    """
    Generate a sequential scrap generation remelt number per calendar year.
    Format: SGR-YYYY-XXXX
    """
    from scrap_generation_remelt.models import ScrapGenerationRemelt

    current_year = date.today().year
    prefix = f"SGR-{current_year}-"

    last_sgr = (
        ScrapGenerationRemelt.objects.filter(remelt_no__startswith=prefix)
        .order_by("-remelt_no")
        .values_list("remelt_no", flat=True)
        .first()
    )

    if last_sgr:
        try:
            seq = int(last_sgr.split("-")[-1])
            new_seq = seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"


def derive_workorder_no_from_salesorder(sales_order_no):
    return sales_order_no


def generate_sales_order_number():
    financial_year = FinancialYearModel.objects.filter(
        start_date__lte=date.today(), end_date__gte=date.today()
    ).first()

    if financial_year:
        year_start = str(financial_year.start_date.year)[-2:]
        year_end = str(financial_year.end_date.year)[-2:]
        financial_year_str = f"{year_start}-{year_end}"
    else:
        financial_year_str = "00-00"

    last_salesorder = (
        InquirySalesOrder.objects.filter(
            sales_order_no__startswith=f"{financial_year_str}"
        )
        .order_by("-id")
        .first()
    )

    if last_salesorder and last_salesorder.sales_order_no:
        last_year_str = last_salesorder.sales_order_no.split("/")[0]

        if last_year_str == financial_year_str:
            last_so_no = int(last_salesorder.sales_order_no.split("/")[-1])
            new_so_no = last_so_no + 1
        else:
            new_so_no = 1
    else:
        new_so_no = 1

    formatted_so_no = f"{financial_year_str}/{new_so_no:04d}"
    return formatted_so_no
