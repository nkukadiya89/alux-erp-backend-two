import logging
import os
import tempfile

from django.core.files.storage import default_storage
from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import ImportJob
from .parsers.csv_parser import CSVParser
from .parsers.excel_parser import ExcelParser
from .services.import_factory import ImportFactory

logger = logging.getLogger(__name__)


class BulkImportView(APIView):
    """Main bulk import endpoint"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle bulk import upload"""
        try:
            if "file" not in request.FILES:
                return Response(
                    {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
                )

            if "model" not in request.data:
                return Response(
                    {"error": "Import model not specified. Use 'model' form field."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            file = request.FILES["file"]
            master_type = str(request.data.get("model", "")).strip().lower()

            if file.size > 10 * 1024 * 1024:
                return Response(
                    {"error": "File size exceeds 10MB limit"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            temp_file_path = self._save_temp_file(file)
            expected_columns_map = {
                "customer_type": {"name"},
                "customertype": {"name"},
                "customer": {
                    "customer_name",
                    "person_name",
                    "phone_number",
                    "email",
                    "gstin_number",
                    "gst_type",
                    "pan_number",
                    "customer_number",
                    "designation",
                    "customer_type",
                    "delivery_days",
                    "udyam_no",
                    "applicable_gst",
                    "office_address_shop",
                    "office_address_area",
                    "office_address_landmark",
                    "office_address_pin_code",
                    "office_address_city",
                    "office_address_state",
                    "office_address_country",
                    "factory_address_shop",
                    "factory_address_area",
                    "factory_address_landmark",
                    "factory_address_pin_code",
                    "factory_address_city",
                    "factory_address_state",
                    "factory_address_country",
                    "customer_section_no",
                    "sales_executive",
                    "sales_executive_assistant",
                    "business_type",
                    "import_export_code",
                    "beneficiary_agent_code",
                    "trade_name",
                    "code",
                    "fax_number",
                    "website",
                    "is_company_visible_on_documents",
                    "credit_limit",
                    "due_days",
                    "licence_no",
                    "note",
                    "customer_balance",
                    "amount",
                    "company_type",
                },
                "bolster_no": {"bloster_no", "press"},
                "alloy": {"Alloy Code", "Standard Name"},
                "temper": {"name"},
                "die": {"die_number"},
                "conversionrate": {
                    "customer",
                    "die",
                    "alloy",
                    "temper",
                    "conversion",
                    "remarks",
                },
                "packingmode": {"name"},
                "sectionpress": {"code"},
                "sectionsize": {"section_height", "section_weight"},
                "vendor": {
                    "person_name",
                    "Contact Person",
                    "contact person",
                    "designation",
                    "email",
                    "phone",
                    "business_type",
                    "import_export_code",
                    "beneficiary_agent_code",
                    "udyam_aadhaar_no",
                    "udyam_aadhaar_no_verified",
                    "vendor_registered_name",
                    "vendor_trade_name",
                    "gst_no",
                    "gst_no_verified",
                    "vendor_code_as_per_company_erp",
                    "pan_number",
                    "code",
                    "fax_number",
                    "website",
                    "is_active",
                    "status",
                    "registered_business_address_building",
                    "registered_business_address_area",
                    "registered_business_address_landmark",
                    "registered_business_address_pincode",
                    "registered_business_address_state",
                    "registered_business_address_city",
                    "registered_business_address_country",
                    "trading_address_building",
                    "trading_address_area",
                    "trading_address_landmark",
                    "trading_address_pincode",
                    "trading_address_state",
                    "trading_address_city",
                    "trading_address_country",
                    "vendor_logo",
                },
                "sectiongroup": {"name"},
                "sectioncategory": {"name"},
                "sectionsubcategory": {"name"},
                "nalco": {"date", "ignot_grade", "rate", "rate_per_mt", "difference"},
            }

            try:
                if temp_file_path.lower().endswith((".xlsx", ".xls")):
                    parser = ExcelParser(temp_file_path)
                else:
                    parser = CSVParser(temp_file_path)

                rows_for_header = parser.parse()
                actual_columns = set()
                if rows_for_header:
                    first = rows_for_header[0]
                    actual_columns = {str(k).strip().lower() for k in first.keys()}
                else:
                    return Response(
                        {"error": "Uploaded file is empty"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                required_fields_map = {
                    "vendor": {"person_name", "email"},
                    "customer_type": {"name"},
                    "customertype": {"name"},
                    "customer": {"customer_name", "phone_number"},
                    "bolster": {"bolster_no", "press"},
                    "alloy": {"Alloy Code", "Standard Name"},
                    "temper": {"name"},
                    "die": {"die_number"},
                    "conversionrate": {
                        "customer",
                        "alloy",
                        "profile_no",
                        "temper",
                        "conversion",
                        "remarks",
                    },
                    "packingmode": {"name"},
                    "sectionpress": {"code"},
                    "sectionsize": {"section_height", "section_weight"},
                    "sectiongroup": {"name"},
                    "sectioncategory": {"name"},
                    "sectionsubcategory": {"name"},
                    "nalco": {"ignot_grade", "date", "rate"},
                }

                if (
                    master_type not in required_fields_map
                    and master_type not in expected_columns_map
                ):
                    return Response(
                        {"error": f"Unsupported import type: {master_type}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                required = required_fields_map.get(master_type, set())
                if required:
                    required_lower = {str(c).strip().lower() for c in required}
                    missing_required = [
                        c
                        for c in required
                        if str(c).strip().lower() not in actual_columns
                    ]
                    if missing_required:
                        logger.error(
                            f"Required columns for {master_type}: {required_lower}"
                        )
                        logger.error(f"Actual columns found: {actual_columns}")
                        logger.error(f"Missing required columns: {missing_required}")
                        return Response(
                            {
                                "error": f"Invalid CSV format..! Please upload the correct CSV/Excel file for {master_type}. Required columns is not Uploaded in CSV/Excel file"
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            except Exception as e:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return Response(
                    {"error": f"Failed to parse uploaded file: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                import_job = ImportJob.objects.create(
                    model_name=master_type,
                    file_name=file.name,
                    file_path=temp_file_path,
                    status="PROCESSING",
                    created_by=request.user,
                )

                importer = ImportFactory.get_importer(master_type, import_job.id)

                from .services.legacy_importer import LegacyImportService

                # Use legacy service for all imports including customer
                if master_type in (
                    "customer",
                    "customer_type",
                    "customertype",
                    "alloy",
                    "temper",
                    "conversionrate",
                    "packingmode",
                    "sectionpress",
                    "vendor",
                    "sectiongroup",
                    "sectionsize",
                    "sectioncategory",
                    "sectionsubcategory",
                    "bloster",
                    "bolster",
                    "nalco",
                ):
                    service = LegacyImportService()
                    compat_response = service.process_file(
                        master_type, temp_file_path, request.user, import_job.id
                    )

                    import_job.total_records = compat_response.get("total_records", 0)
                    import_job.success_records = compat_response.get(
                        "inserted", 0
                    ) + compat_response.get("updated", 0)
                    import_job.failed_records = compat_response.get("failed", 0)
                    import_job.status = "COMPLETED"
                    import_job.save()

                    return Response(compat_response, status=status.HTTP_200_OK)
                else:
                    result = importer.process(temp_file_path, request.user)

                import_job.total_records = result.get("total", 0)
                import_job.success_records = result.get("success", 0)
                import_job.failed_records = result.get("failed", 0)
                import_job.status = "COMPLETED"
                import_job.save()

                if master_type in ("customer_type", "customertype"):
                    total = result.get("total", 0)
                    inserted = result.get("success", 0)
                    updated = 0
                    skipped = 0
                    failed = result.get("failed", 0)

                    message_parts = []
                    if inserted > 0:
                        message_parts.append(
                            f"{inserted} records inserted successfully"
                        )
                    if updated > 0:
                        message_parts.append(f"{updated} records updated successfully")
                    if skipped > 0:
                        message_parts.append(f"{skipped} record skipped successfully")
                    if failed > 0:
                        message_parts.append(f"{failed} records failed")

                    compat_response = {
                        "success": bool(inserted or updated or skipped),
                        "total_records": total,
                        "inserted": inserted,
                        "updated": updated,
                        "skipped": skipped,
                        "failed": failed,
                        "message": (
                            " | ".join(message_parts)
                            if message_parts
                            else "No records processed"
                        ),
                    }

                    # if result.get('errors'):
                    #     compat_response['errors'] = result.get('errors')

                    # Return compat response (no job_id wrapper) to match old format
                    return Response(compat_response, status=status.HTTP_200_OK)

                return Response(
                    {
                        "success": True,
                        "job_id": import_job.job_id,
                        "result": result,
                        "importer_class": f"class {importer.__class__.__name__}(BaseImporter):",
                    },
                    status=status.HTTP_200_OK,
                )

            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        except Exception as e:
            logger.error(f"Bulk import error: {str(e)}")
            return Response(
                {"error": f"Import failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _save_temp_file(self, file):
        """Save uploaded file to temporary location"""
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f"_{file.name}"
        ) as temp_file:
            for chunk in file.chunks():
                temp_file.write(chunk)
            return temp_file.name

    def get(self, request):
        """Get supported import types"""
        supported_types = ImportFactory.get_supported_types()
        return Response({"supported_types": supported_types})


class ImportStatusView(APIView):
    """Check import job status"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        """Get import job status"""
        try:
            import_job = ImportJob.objects.get(job_id=job_id, created_by=request.user)

            return Response(
                {
                    "job_id": import_job.job_id,
                    "status": import_job.status,
                    "total_records": import_job.total_records,
                    "success_records": import_job.success_records,
                    "failed_records": import_job.failed_records,
                    "created_at": import_job.created_at,
                    "completed_at": import_job.completed_at,
                }
            )
        except ImportJob.DoesNotExist:
            return Response(
                {"error": "Import job not found"}, status=status.HTTP_404_NOT_FOUND
            )
