from typing import Any, Dict, List, Optional

from django.db import transaction

from vendor.models import BankDetails, KeyPersons, Vendor

from ..services.base_importer import BaseImporter


class VendorImporter(BaseImporter):
    model = Vendor
    unique_field = "email"

    def _vendor_fields(self):
        return {
            "person_name",
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
        }

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        field_mapping = {
            "person_name": ["person_name", "Person Name"],
            "designation": ["designation", "Designation"],
            "email": ["email", "Email"],
            "phone": ["phone", "Phone"],
            "business_type": ["business_type", "Business Type"],
            "vendor_registered_name": ["vendor_registered_name"],
            "vendor_trade_name": ["vendor_trade_name"],
            "gst_no": ["gst_no"],
            "pan_number": ["pan_number"],
            "import_export_code": ["import_export_code"],
            "beneficiary_agent_code": ["beneficiary_agent_code"],
            "udyam_aadhaar_no": ["udyam_aadhaar_no"],
            "udyam_aadhaar_no_verified": ["udyam_aadhaar_no_verified"],
            "gst_no_verified": ["gst_no_verified"],
            "vendor_code_as_per_company_erp": ["vendor_code_as_per_company_erp"],
            "code": ["code"],
            "fax_number": ["fax_number"],
            "website": ["website"],
            "is_active": ["is_active"],
            "status": ["status"],
            "registered_business_address_building": [
                "registered_business_address_building"
            ],
            "registered_business_address_area": ["registered_business_address_area"],
            "registered_business_address_landmark": [
                "registered_business_address_landmark"
            ],
            "registered_business_address_pincode": [
                "registered_business_address_pincode"
            ],
            "registered_business_address_state": ["registered_business_address_state"],
            "registered_business_address_city": ["registered_business_address_city"],
            "registered_business_address_country": [
                "registered_business_address_country"
            ],
            "trading_address_building": ["trading_address_building"],
            "trading_address_area": ["trading_address_area"],
            "trading_address_landmark": ["trading_address_landmark"],
            "trading_address_pincode": ["trading_address_pincode"],
            "trading_address_state": ["trading_address_state"],
            "trading_address_city": ["trading_address_city"],
            "trading_address_country": ["trading_address_country"],
            "vendor_logo": ["vendor_logo"],
            # Key Person
            "key_person_name": ["key_person_name"],
            "key_person_designation": ["key_person_designation"],
            "key_person_email": ["key_person_email"],
            "key_person_contact": ["key_person_contact"],
            # Bank
            "bank_name": ["bank_name"],
            "bank_account_number": ["bank_account_number"],
            "bank_ifsc_code": ["bank_ifsc_code"],
            "branch_address": ["branch_address"],
            "bank_ad_code": ["bank_ad_code"],
            "beneficiary_swift_code": ["beneficiary_swift_code"],
        }

        data = {}
        for target, keys in field_mapping.items():
            for k in keys:
                if k in row and row[k] not in ("", None):
                    val = row[k]
                    if target in [
                        "udyam_aadhaar_no_verified",
                        "gst_no_verified",
                        "is_active",
                    ]:
                        val = str(val).lower() in ["1", "true", "yes", "y"]
                    data[target] = val
                    break
        return data

    def _validate_row(self, data: Dict, row_num: int):
        if not data.get("email"):
            return False, f"Row {row_num}: email is required"
        if not data.get("person_name"):
            return False, f"Row {row_num}: person_name is required"
        return True, None

    def _normalize_field_value(self, field, value):
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        return str(value).strip()

    def _is_exact_duplicate(self, instance, data):
        for field in self._vendor_fields():
            old = getattr(instance, field, None)
            new = data.get(field)
            if self._normalize_field_value(field, old) != self._normalize_field_value(
                field, new
            ):
                return False
        return True

    def process_rows(self, rows: List[Dict], user) -> Dict:
        result = {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}

        for idx, row in enumerate(rows, start=2):
            try:
                data = self.normalize(row)
                valid, msg = self._validate_row(data, idx)
                if not valid:
                    result["failed"] += 1
                    continue

                with transaction.atomic():
                    vendor = Vendor.objects.filter(email=data["email"]).first()

                    gst_no = data.get("gst_no")
                    if gst_no and gst_no.strip():
                        gst_vendor = Vendor.objects.filter(
                            gst_no=gst_no.strip()
                        ).first()
                        if gst_vendor and gst_vendor.email != data["email"]:
                            result["failed"] += 1
                            continue

                    pan_number = data.get("pan_number")
                    if pan_number and pan_number.strip():
                        pan_vendor = Vendor.objects.filter(
                            pan_number=pan_number.strip()
                        ).first()
                        if pan_vendor and pan_vendor.email != data["email"]:
                            result["failed"] += 1
                            continue

                    if vendor:
                        if self._is_exact_duplicate(vendor, data):
                            result["skipped"] += 1
                        else:
                            changed = False
                            for field in self._vendor_fields():
                                new = data.get(field)
                                old = getattr(vendor, field, None)
                                if self._normalize_field_value(
                                    field, old
                                ) != self._normalize_field_value(field, new):
                                    setattr(vendor, field, new)
                                    changed = True

                            if changed:
                                vendor.updated_by = user
                                vendor.save()
                                result["updated"] += 1
                    else:
                        vendor = Vendor.objects.create(
                            **{f: data.get(f) for f in self._vendor_fields()},
                            created_by=user,
                            updated_by=user,
                        )
                        result["inserted"] += 1

                    if data.get("key_person_email"):
                        KeyPersons.objects.get_or_create(
                            vendor=vendor,
                            email=data["key_person_email"],
                            defaults={
                                "person_name": data.get("key_person_name"),
                                "designation": data.get("key_person_designation"),
                                "contact_number": data.get("key_person_contact"),
                                "created_by": user,
                            },
                        )

                    if data.get("bank_account_number"):
                        BankDetails.objects.get_or_create(
                            vendor=vendor,
                            bank_account_number=data["bank_account_number"],
                            defaults={
                                "bank_name": data.get("bank_name"),
                                "bank_ifsc_code": data.get("bank_ifsc_code"),
                                "branch_address": data.get("branch_address"),
                                "bank_ad_code": data.get("bank_ad_code"),
                                "beneficiary_swift_code": data.get(
                                    "beneficiary_swift_code"
                                ),
                                "created_by": user,
                            },
                        )

            except Exception:
                result["failed"] += 1

        total = len(rows)
        message_parts = []
        if result["inserted"]:
            message_parts.append(f"{result['inserted']} records inserted successfully")
        if result["updated"]:
            message_parts.append(f"{result['updated']} records updated successfully")
        if result["skipped"]:
            message_parts.append(f"{result['skipped']} record skipped successfully")
        if result["failed"]:
            message_parts.append(f"{result['failed']} records failed")

        return {
            "success": bool(
                result["inserted"] or result["updated"] or result["skipped"]
            ),
            "total_records": total,
            "inserted": result["inserted"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "failed": result["failed"],
            "message": (
                " | ".join(message_parts) if message_parts else "No records processed"
            ),
        }
