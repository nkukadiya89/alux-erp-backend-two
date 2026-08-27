from django.apps.registry import Apps
from django.db import router
from rest_framework import routers

from aging.routers import aging_routers
from bloster.routers import bloster_routers
from bulk_import.routers import bulkimportrouters
from bundle_inward.routers import bundle_inward_routers
from bundle_outward.routers import bundle_outward_routers
from bundle_verification.routers import bundle_verification_routers
from common.routers import common_routers
from current_stock.routers import current_stock_routers
from customer.routers import customer_routers
from die.routers import die_routers
from die_proforma.routers import die_proforma_router
from die_quotation.routers import die_quotation_routers
from die_requisition.routers import die_requisition_router
from dimension_inspection.routers import dimension_inspection_routers
from first_weight_entry.routers import first_weight_entry_routers
from inquiry.routers import inquiry_routers
from inquiry_quotation.routers import inquiry_quotation_routers
from inquiry_salesorder.routers import inquiry_salesorder_routers
from manual_weight_entry.routers import manual_weight_entry_routers
from material.routers import material_routers
from gate_entry.routers import gate_entry_routers
from gate_pass.routers import gate_pass_routers
from scrap_sale.routers import scrap_sale_routers
from scrap_entry.routers import scrap_entry_routers
from scrap_transfer.routers import scrap_transfer_routers
from scrap_generation_remelt.routers import scrap_generation_remelt_routers
from melting_furnace.routers import melting_furnace_routers
from shift_logs.routers import shiftlog_router
from online_inspection.routers import router as online_inspection_router

# from fileupload.router import file_upload_routers
from msg_logger.routers import activity_log_routers
from nalco.routers import nalco_routers
from party.routers import party_routers
from planning.routers import planning_routers
from product.routers import product_routers
from production.routers import production_routers
from proforma.routers import proforma_routers
from quotation.routers import quotation_routers
from second_weight_entry.routers import second_weight_entry_routers
from settings.routers import settings_routers
from shift.routers import shift_router
from store.routers import store_routers
from transporter.routers import transporter_routers
from user.routers import user_routers
from vehicle_master.routers import vehiclemaster_routers
from vehicle_type.routers import vehicletype_routers
from vendor.routers import vendor_routers
from warehouse.routers import warehouse_routers
from workorder.routers import workorder_routers
from mechanical_test.routers import mechanical_test_routers
from jobwork_invoice.routers import jobwork_invoice_routers
from return_qc.routers import return_qc_routers
from test_certificate.routers import test_certificate_router
from dietool_production.routers import dieproductionlog_routers
from material_indent.routers import material_indent_router
from material_request.routers import material_request_router
from receipt_notes.routers import receipt_notes_router
from furnace_master.routers import furnace_master_router
from quality_inspection.routers import quality_inspection_router
from return_to_vendor.routers import rtv_router
from ageing_cycle.routers import ageing_cycle_routers
from purchase_order.routers import purchase_order_router

from recovery_standard_master.routers import recovery_standard_master
from furnace_charge_plan.routers import furnace_charge_plan_router
from create_dross_entry.routers import create_dross_entry_routers
alux_router = routers.DefaultRouter()

alux_router.registry.extend(bulkimportrouters.registry)
alux_router.registry.extend(manual_weight_entry_routers.registry)
alux_router.registry.extend(second_weight_entry_routers.registry)
alux_router.registry.extend(first_weight_entry_routers.registry)
alux_router.registry.extend(material_routers.registry)
alux_router.registry.extend(vehiclemaster_routers.registry)
alux_router.registry.extend(vehicletype_routers.registry)
alux_router.registry.extend(transporter_routers.registry)
alux_router.registry.extend(common_routers.registry)
alux_router.registry.extend(user_routers.registry)
alux_router.registry.extend(die_routers.registry)
alux_router.registry.extend(party_routers.registry)
alux_router.registry.extend(quotation_routers.registry)
alux_router.registry.extend(workorder_routers.registry)
alux_router.registry.extend(product_routers.registry)
alux_router.registry.extend(bloster_routers.registry)
alux_router.registry.extend(vendor_routers.registry)
alux_router.registry.extend(customer_routers.registry)
alux_router.registry.extend(nalco_routers.registry)
alux_router.registry.extend(die_proforma_router.registry)
alux_router.registry.extend(die_quotation_routers.registry)
alux_router.registry.extend(proforma_routers.registry)
alux_router.registry.extend(bundle_inward_routers.registry)
alux_router.registry.extend(bundle_outward_routers.registry)
alux_router.registry.extend(current_stock_routers.registry)
alux_router.registry.extend(planning_routers.registry)
alux_router.registry.extend(aging_routers.registry)
alux_router.registry.extend(warehouse_routers.registry)
alux_router.registry.extend(bundle_verification_routers.registry)
alux_router.registry.extend(production_routers.registry)
alux_router.registry.extend(activity_log_routers.registry)
alux_router.registry.extend(inquiry_salesorder_routers.registry)
alux_router.registry.extend(inquiry_routers.registry)
alux_router.registry.extend(inquiry_quotation_routers.registry)
alux_router.registry.extend(shift_router.registry)
alux_router.registry.extend(settings_routers.registry)
alux_router.registry.extend(store_routers.registry)
alux_router.registry.extend(die_requisition_router.registry)
alux_router.registry.extend(melting_furnace_routers.registry)
alux_router.registry.extend(shiftlog_router.registry)
alux_router.registry.extend(gate_pass_routers.registry)
alux_router.registry.extend(gate_entry_routers.registry)
alux_router.registry.extend(scrap_sale_routers.registry)
alux_router.registry.extend(scrap_entry_routers.registry)
alux_router.registry.extend(scrap_transfer_routers.registry)
alux_router.registry.extend(scrap_generation_remelt_routers.registry)
alux_router.registry.extend(online_inspection_router.registry)
alux_router.registry.extend(dimension_inspection_routers.registry)
alux_router.registry.extend(mechanical_test_routers.registry)
alux_router.registry.extend(jobwork_invoice_routers.registry)
alux_router.registry.extend(return_qc_routers.registry)
alux_router.registry.extend(test_certificate_router.registry)
alux_router.registry.extend(dieproductionlog_routers.registry)
alux_router.registry.extend(material_indent_router.registry)
alux_router.registry.extend(material_request_router.registry)
alux_router.registry.extend(receipt_notes_router.registry)
alux_router.registry.extend(furnace_master_router.registry)
alux_router.registry.extend(quality_inspection_router.registry)
alux_router.registry.extend(rtv_router.registry)
alux_router.registry.extend(ageing_cycle_routers.registry)
alux_router.registry.extend(purchase_order_router.registry)
# alux_router.registry.extend(file_upload_routers.registry)
alux_router.registry.extend(recovery_standard_master.registry)
alux_router.registry.extend(furnace_charge_plan_router.registry)
alux_router.registry.extend(create_dross_entry_routers.registry)