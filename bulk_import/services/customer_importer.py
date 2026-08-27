# bulk_import/services/customer_importer.py
import random
import re
import string
from typing import Any, Dict, List, Optional

from django.db import transaction

from customer.models import BankingDetails, ContactPerson, Customer

from ..services.base_importer import BaseImporter


class CustomerImporter(BaseImporter):
    """Customer bulk importer"""

    model = Customer
    unique_field = "customer_number"

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)

    def _customer_fields(self):
        return {
            "customer_name",
            "customer_number",
            "person_name",
            "designation",
            "email",
            "phone_number",
            "customer_type",
            "delivery_days",
            "udyam_no",
            "applicable_gst",
            "gstin_number",
            "gst_type",
            "pan_number",
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
        }

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize customer row data"""
        field_mapping = {
            "Customer Name": "customer_name",
            "Company Name": "customer_name",
            "customer_name": "customer_name",
            "Person Name": "person_name",
            "Contact Person": "person_name",
            "person_name": "person_name",
            "Phone": "phone_number",
            "Phone Number": "phone_number",
            "Mobile": "phone_number",
            "phone_number": "phone_number",
            "Email": "email",
            "Email Address": "email",
            "email": "email",
            "GSTIN": "gstin_number",
            "GST Number": "gstin_number",
            "GSTIN Number": "gstin_number",
            "gstin_number": "gstin_number",
            "GST Type": "gst_type",
            "gst_type": "gst_type",
            "PAN": "pan_number",
            "PAN Number": "pan_number",
            "pan_number": "pan_number",
            "Customer Number": "customer_number",
            "Customer Code": "customer_number",
            "customer_number": "customer_number",
            "Designation": "designation",
            "designation": "designation",
            "Customer Type": "customer_type",
            "Type": "customer_type",
            "customer_type": "customer_type",
            "Business Type": "business_type",
            "business_type": "business_type",
            "Delivery Days": "delivery_days",
            "delivery_days": "delivery_days",
            "Udyam No": "udyam_no",
            "udyam_no": "udyam_no",
            "Applicable GST": "applicable_gst",
            "applicable_gst": "applicable_gst",
            "Office Shop": "office_address_shop",
            "Office Address Shop": "office_address_shop",
            "office_address_shop": "office_address_shop",
            "Office Area": "office_address_area",
            "Office Address Area": "office_address_area",
            "office_address_area": "office_address_area",
            "Office Landmark": "office_address_landmark",
            "office_address_landmark": "office_address_landmark",
            "Office City": "office_address_city",
            "Office Address City": "office_address_city",
            "office_address_city": "office_address_city",
            "Office State": "office_address_state",
            "Office Address State": "office_address_state",
            "office_address_state": "office_address_state",
            "Office Pincode": "office_address_pin_code",
            "Office Pin Code": "office_address_pin_code",
            "office_address_pin_code": "office_address_pin_code",
            "Office Country": "office_address_country",
            "office_address_country": "office_address_country",
            "Factory Shop": "factory_address_shop",
            "factory_address_shop": "factory_address_shop",
            "Factory Area": "factory_address_area",
            "factory_address_area": "factory_address_area",
            "Factory Landmark": "factory_address_landmark",
            "factory_address_landmark": "factory_address_landmark",
            "Factory City": "factory_address_city",
            "factory_address_city": "factory_address_city",
            "Factory State": "factory_address_state",
            "factory_address_state": "factory_address_state",
            "Factory Pincode": "factory_address_pin_code",
            "factory_address_pin_code": "factory_address_pin_code",
            "Factory Country": "factory_address_country",
            "factory_address_country": "factory_address_country",
            "Customer Section No": "customer_section_no",
            "customer_section_no": "customer_section_no",
            "Sales Executive": "sales_executive",
            "sales_executive": "sales_executive",
            "Sales Executive Assistant": "sales_executive_assistant",
            "sales_executive_assistant": "sales_executive_assistant",
            "Import Export Code": "import_export_code",
            "IEC": "import_export_code",
            "import_export_code": "import_export_code",
            "Beneficiary Agent Code": "beneficiary_agent_code",
            "beneficiary_agent_code": "beneficiary_agent_code",
            "Trade Name": "trade_name",
            "trade_name": "trade_name",
            "Code": "code",
            "code": "code",
            "Fax Number": "fax_number",
            "fax_number": "fax_number",
            "Website": "website",
            "website": "website",
            "Is Company Visible On Documents": "is_company_visible_on_documents",
            "is_company_visible_on_documents": "is_company_visible_on_documents",
            "Credit Limit": "credit_limit",
            "credit_limit": "credit_limit",
            "Due Days": "due_days",
            "due_days": "due_days",
            "Licence No": "licence_no",
            "licence_no": "licence_no",
            "Note": "note",
            "note": "note",
            "Customer Balance": "customer_balance",
            "customer_balance": "customer_balance",
            "Amount": "amount",
            "amount": "amount",
            "Company Type": "company_type",
            "company_type": "company_type",
            # Contact Person
            "Contact Person Name": "contact_person_name",
            "contact_person_name": "contact_person_name",
            "Contact Person Designation": "contact_person_designation",
            "contact_person_designation": "contact_person_designation",
            "Contact Person Mobile": "contact_person_mobile_number",
            "Contact Person Mobile Number": "contact_person_mobile_number",
            "contact_person_mobile_number": "contact_person_mobile_number",
            "Contact Person Email": "contact_person_email",
            "contact_person_email": "contact_person_email",
            # Banking Details
            "Bank Name": "bank_name",
            "bank_name": "bank_name",
            "Bank Account Number": "bank_account_number",
            "bank_account_number": "bank_account_number",
            "Bank IFSC Code": "bank_ifsc_code",
            "bank_ifsc_code": "bank_ifsc_code",
            "Bank Branch Address": "bank_branch_address",
            "bank_branch_address": "bank_branch_address",
            "Beneficiary Swift Code": "beneficiary_swift_code",
            "beneficiary_swift_code": "beneficiary_swift_code",
            "Bank AD Code": "bank_ad_code",
            "bank_ad_code": "bank_ad_code",
        }
        normalized_row = {}

        for key, value in row.items():
            if key in field_mapping:
                field_name = field_mapping[key]
                normalized_value = self._normalize_field_value(field_name, value)
                if normalized_value is not None:
                    normalized_row[field_name] = normalized_value

        if not normalized_row.get("customer_number") and normalized_row.get(
            "customer_name"
        ):
            normalized_row["customer_number"] = self._generate_customer_number(
                normalized_row["customer_name"]
            )

        if not normalized_row.get("business_type"):
            normalized_row["business_type"] = "INDIAN"

        return normalized_row

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        """Normalize individual field values"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        value_str = str(value).strip()

        if field_name == "phone_number":
            return self._normalize_phone(value_str)
        elif field_name == "email":
            return self._normalize_email(value_str)
        elif field_name in ["gstin_number", "pan_number"]:
            return value_str.upper()
        elif field_name == "business_type":
            return self._normalize_business_type(value_str)
        elif field_name == "delivery_days":
            return self._normalize_numeric(value_str)
        elif field_name in ["due_days", "credit_limit"]:
            return self._normalize_decimal(value_str)
        elif field_name == "is_company_visible_on_documents":
            return self._normalize_boolean(value_str)
        elif field_name in ["customer_name", "person_name"]:
            return self._normalize_text(value_str)
        else:
            return value_str

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number"""
        phone_digits = re.sub(r"\D", "", phone)

        if len(phone_digits) == 10:
            return phone_digits
        elif len(phone_digits) == 11 and phone_digits.startswith("0"):
            return phone_digits[1:]
        elif len(phone_digits) == 13 and phone_digits.startswith("91"):
            return phone_digits[2:]

        return phone_digits

    def _normalize_email(self, email: str) -> str:
        """Normalize email"""
        return email.lower().strip()

    def _normalize_business_type(self, business_type: str) -> str:
        """Normalize business type"""
        business_type_upper = business_type.upper().strip()

        mapping = {
            "INDIAN": "INDIAN",
            "INDIA": "INDIAN",
            "DOMESTIC": "INDIAN",
            "LOCAL": "INDIAN",
            "OVERSEAS": "OVERSEAS",
            "INTERNATIONAL": "OVERSEAS",
            "EXPORT": "OVERSEAS",
            "FOREIGN": "OVERSEAS",
        }

        return mapping.get(business_type_upper, business_type_upper)

    def _normalize_numeric(self, value: str) -> int:
        """Normalize numeric fields"""
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _normalize_text(self, text: str) -> str:
        """Normalize text fields"""
        return " ".join(text.split()).title()

    def _normalize_decimal(self, value: str) -> float:
        """Normalize decimal fields"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _normalize_boolean(self, value: str) -> bool:
        """Normalize boolean fields"""
        if isinstance(value, bool):
            return value
        value_str = str(value).strip().lower()
        return value_str in ("true", "1", "yes", "on")

    def _generate_customer_number(self, customer_name: str) -> str:
        """Auto-generate customer number from customer name"""
        clean_name = re.sub(r"[^a-zA-Z0-9\s]", "", customer_name)
        words = clean_name.upper().split()

        if len(words) >= 2:
            code = words[0][:3] + words[1][:3]
        else:
            code = clean_name[:6].upper()
        suffix = "".join(random.choices(string.digits, k=3))

        return f"CUST{code}{suffix}"

    def validate(self, data: Dict[str, Any]):
        """Skip base validation"""
        pass

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        """Validate required fields"""
        if not data.get("customer_name"):
            return False, f"Row {row_num}: Customer name is required"
        if not data.get("phone_number"):
            return False, f"Row {row_num}: Phone number is required"
        return True, None

    def _is_exact_duplicate(self, existing, mapped):
        """Check if all fields match exactly"""
        for field, new_val in mapped.items():
            if field in [
                "id",
                "created_by",
                "updated_by",
                "created_at",
                "updated_at",
                "deleted",
                "deleted_at",
            ]:
                continue

            old_val = getattr(existing, field, None)

            # Normalize both values for consistent comparison
            normalized_old = self._normalize_field_value(field, old_val)
            normalized_new = self._normalize_field_value(field, new_val)

            if normalized_old != normalized_new:
                return False
        return True

    def process_rows(self, rows: List[Dict], user) -> Dict:
        """Process customer rows"""
        result = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "inserted_rows": [],
            "skipped_rows": [],
        }

        for idx, row in enumerate(rows, start=2):
            try:
                mapped = self.normalize(row)

                valid, msg = self._validate_row(mapped, idx)
                if not valid:
                    result["skipped"] += 1
                    result["skipped_rows"].append({"row_number": idx, "reason": msg})
                    continue

                with transaction.atomic():
                    lookup = {"customer_number": mapped.get("customer_number")}
                    existing = self.model.objects.filter(**lookup).first()

                    if existing:
                        if self._is_exact_duplicate(existing, mapped):
                            result["skipped"] += 1
                            result["skipped_rows"].append(
                                {
                                    "row_number": idx,
                                    "customer": mapped.get("customer_name"),
                                }
                            )
                        else:
                            changed = False

                        if "customer_type" in mapped and isinstance(
                            mapped["customer_type"], str
                        ):
                            try:
                                from customer.models import CustomerType

                                customer_type_name = mapped["customer_type"]
                                customer_type_instance = CustomerType.objects.get(
                                    name=customer_type_name
                                )
                                mapped["customer_type"] = customer_type_instance
                            except CustomerType.DoesNotExist:
                                try:
                                    customer_type_instance = CustomerType.objects.get(
                                        name__iexact=customer_type_name
                                    )
                                    mapped["customer_type"] = customer_type_instance
                                except CustomerType.DoesNotExist:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"CustomerType '{customer_type_name}' not found",
                                        }
                                    )
                                    continue

                        if "sales_executive" in mapped and isinstance(
                            mapped["sales_executive"], str
                        ):
                            sales_exec_username = mapped["sales_executive"]
                            try:
                                from user.models import User

                                sales_exec_instance = User.objects.get(
                                    username=sales_exec_username
                                )
                                mapped["sales_executive"] = sales_exec_instance
                            except User.DoesNotExist:
                                try:
                                    sales_exec_instance = User.objects.get(
                                        username__iexact=sales_exec_username
                                    )
                                    mapped["sales_executive"] = sales_exec_instance
                                except User.DoesNotExist:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"User '{sales_exec_username}' not found",
                                        }
                                    )
                                    continue

                        if "sales_executive_assistant" in mapped and isinstance(
                            mapped["sales_executive_assistant"], str
                        ):
                            assistant_username = mapped["sales_executive_assistant"]
                            try:
                                from user.models import User

                                assistant_instance = User.objects.get(
                                    username=assistant_username
                                )
                                mapped["sales_executive_assistant"] = assistant_instance
                            except User.DoesNotExist:
                                try:
                                    assistant_instance = User.objects.get(
                                        username__iexact=assistant_username
                                    )
                                    mapped["sales_executive_assistant"] = (
                                        assistant_instance
                                    )
                                except User.DoesNotExist:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"User '{assistant_username}' not found",
                                        }
                                    )
                                    continue

                        for k, v in mapped.items():
                            if self._normalize_field_value(
                                k, getattr(existing, k, None)
                            ) != self._normalize_field_value(k, v):
                                setattr(existing, k, v)
                                changed = True
                        if changed:
                            existing.updated_by = user
                            existing.save()
                            result["updated"] += 1
                        else:
                            result["skipped"] += 1
                            result["skipped_rows"].append(
                                {"row_number": idx, "customer": existing.customer_name}
                            )

                        customer = existing
                    else:
                        if "customer_type" in mapped and isinstance(
                            mapped["customer_type"], str
                        ):
                            try:
                                from customer.models import CustomerType

                                customer_type_name = mapped["customer_type"]
                                customer_type_instance = CustomerType.objects.get(
                                    name=customer_type_name
                                )
                                mapped["customer_type"] = customer_type_instance
                            except CustomerType.DoesNotExist:
                                try:
                                    customer_type_instance = CustomerType.objects.get(
                                        name__iexact=customer_type_name
                                    )
                                    mapped["customer_type"] = customer_type_instance
                                except CustomerType.DoesNotExist:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"CustomerType '{customer_type_name}' not found",
                                        }
                                    )
                                    continue

                        if "sales_executive" in mapped and isinstance(
                            mapped["sales_executive"], str
                        ):
                            try:
                                from user.models import User

                                sales_exec_username = mapped["sales_executive"]
                                sales_exec_instance = User.objects.get(
                                    username=sales_exec_username
                                )
                                mapped["sales_executive"] = sales_exec_instance
                            except User.DoesNotExist:
                                try:
                                    sales_exec_instance = User.objects.get(
                                        username__iexact=sales_exec_username
                                    )
                                    mapped["sales_executive"] = sales_exec_instance
                                except User.DoesNotExist:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"User '{sales_exec_username}' not found",
                                        }
                                    )
                                    continue

                        if "sales_executive_assistant" in mapped and isinstance(
                            mapped["sales_executive_assistant"], str
                        ):
                            assistant_username = mapped["sales_executive_assistant"]
                            try:
                                from user.models import User

                                assistant_instance = User.objects.get(
                                    username=assistant_username
                                )
                                mapped["sales_executive_assistant"] = assistant_instance
                            except User.DoesNotExist:
                                try:
                                    assistant_instance = User.objects.get(
                                        username__iexact=assistant_username
                                    )
                                    mapped["sales_executive_assistant"] = (
                                        assistant_instance
                                    )
                                except User.DoesNotExist:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"User '{assistant_username}' not found",
                                        }
                                    )
                                    continue

                        customer_data = {
                            f: mapped.get(f)
                            for f in self._customer_fields()
                            if f in mapped
                        }
                        customer = self.model.objects.create(
                            **customer_data, created_by=user, updated_by=user
                        )
                        result["inserted"] += 1
                        result["inserted_rows"].append({"row_number": idx})

                    # Handle Contact Person
                    if mapped.get("contact_person_mobile_number"):
                        ContactPerson.objects.get_or_create(
                            customer=customer,
                            contact_person_mobile_number=mapped[
                                "contact_person_mobile_number"
                            ],
                            defaults={
                                "contact_person_name": mapped.get(
                                    "contact_person_name"
                                ),
                                "contact_person_designation": mapped.get(
                                    "contact_person_designation"
                                ),
                                "contact_person_email": mapped.get(
                                    "contact_person_email"
                                ),
                                "created_by": user,
                                "updated_by": user,
                            },
                        )

                    # Handle Banking Details
                    if mapped.get("bank_account_number"):
                        BankingDetails.objects.get_or_create(
                            customer=customer,
                            bank_account_number=mapped["bank_account_number"],
                            defaults={
                                "bank_name": mapped.get("bank_name"),
                                "bank_ifsc_code": mapped.get("bank_ifsc_code"),
                                "bank_branch_address": mapped.get(
                                    "bank_branch_address"
                                ),
                                "beneficiary_swift_code": mapped.get(
                                    "beneficiary_swift_code"
                                ),
                                "bank_ad_code": mapped.get("bank_ad_code"),
                                "created_by": user,
                                "updated_by": user,
                            },
                        )

            except Exception as e:
                result["skipped"] += 1
                result["skipped_rows"].append({"row_number": idx, "reason": str(e)})

        message_parts = []
        if result["inserted"]:
            message_parts.append(f"{result['inserted']} records inserted successfully")
        if result["updated"]:
            message_parts.append(f"{result['updated']} records updated successfully")
        if result["skipped"]:
            message_parts.append(f"{result['skipped']} record skipped successfully")

        response = {
            "success": bool(
                result["inserted"] or result["updated"] or result["skipped"]
            ),
            "total_records": len(rows),
            "inserted": result["inserted"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "message": (
                " | ".join(message_parts) if message_parts else "No records processed"
            ),
        }

        if result["inserted_rows"]:
            nums = [str(x["row_number"]) for x in result["inserted_rows"]]
            display = ", ".join(nums[:10])
            extra = f"... ({len(nums)} total)" if len(nums) > 10 else ""
            response["success_message"] = f"Newly added rows: Row {display}{extra}"

        if result["skipped_rows"]:
            response["skipped_details"] = result["skipped_rows"][:20]

        return response
