"""
Customer Master bulk importer
Implements BaseImporter for Customer module
"""

import logging
from typing import Dict, List

from django.db import IntegrityError, transaction
from django.forms.models import model_to_dict
from django.utils import timezone

from customer.models import BankingDetails, ContactPerson, Customer, CustomerType
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_choice, normalize_string
from imports.validators.field_validators import (
    ChoiceValidator,
    EmailValidator,
    StringValidator,
    UniqueValidator,
)
from imports.validators.reference_validators import ForeignKeyValidator
from user.models import User

logger = logging.getLogger(__name__)


class CustomerImporter(BaseImporter):
    """
    Bulk importer for Customer Master module
    """

    MODULE_NAME = "Customer"
    REQUIRED_COLUMNS = [
        "Customer Name",
        "Person Name",
        "Phone Number",
        "Business Type",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_customer_names = set()
        self.seen_licence_nos = set()  
        self.seen_gstin_numbers = set()
        self.seen_pan_numbers = set()  
        self.seen_udyam_nos = set()  
        self.customer_type_cache = {} 
        self.user_cache = {}  
        self.row_number_map = {}

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Customer Name": "customer_name",
            "Person Name": "person_name",
            "Designation": "designation",
            "Email": "email",
            "Phone Number": "phone_number",
            "Business Type": "business_type",
            "Company Type": "company_type",
            "GSTIN Number": "gstin_number",
            "GST Type": "gst_type",
            "PAN Number": "pan_number",
            "Udyam No": "udyam_no",
            "Applicable GST": "applicable_gst",
            "Trade Name": "trade_name",
            "Code": "code",
            "Fax Number": "fax_number",
            "Website": "website",
            "Customer Type": "customer_type",
            "Sales Executive": "sales_executive",
            "Sales Executive Assistant": "sales_executive_assistant",
            "Delivery Days": "delivery_days",
            "Is Company Visible On Documents": "is_company_visible_on_documents",
            "Credit Limit": "credit_limit",
            "Due Days": "due_days",
            "Licence No": "licence_no",
            "Note": "note",
            "Customer Balance": "customer_balance",
            "Import Export Code": "import_export_code",
            "Beneficiary Agent Code": "beneficiary_agent_code",
            "Office Address Shop": "office_address_shop",
            "Office Address Area": "office_address_area",
            "Office Address Landmark": "office_address_landmark",
            "Office Address Pin Code": "office_address_pin_code",
            "Office Address City": "office_address_city",
            "Office Address State": "office_address_state",
            "Office Address Country": "office_address_country",
            "Factory Address Shop": "factory_address_shop",
            "Factory Address Area": "factory_address_area",
            "Factory Address Landmark": "factory_address_landmark",
            "Factory Address Pin Code": "factory_address_pin_code",
            "Factory Address City": "factory_address_city",
            "Factory Address State": "factory_address_state",
            "Factory Address Country": "factory_address_country",
            "Contact Person Name": "contact_person_name",
            "Contact Person Designation": "contact_person_designation",
            "Contact Person Mobile Number": "contact_person_mobile_number",
            "Contact Person Email": "contact_person_email",
            "Bank Name": "bank_name",
            "Bank Account Number": "bank_account_number",
            "Bank IFSC Code": "bank_ifsc_code",
            "Bank Branch Address": "bank_branch_address",
            "Beneficiary Swift Code": "beneficiary_swift_code",
            "Bank AD Code": "bank_ad_code",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        return {
            "customer_name": [
                UniqueValidator(
                    "customer_name", self.seen_customer_names, required=True
                ),
                StringValidator("customer_name", max_length=255, required=True),
            ],
            "person_name": [
                StringValidator("person_name", max_length=250, required=True)
            ],
            "phone_number": [
                StringValidator("phone_number", max_length=15, required=True)
            ],
            "email": [EmailValidator("email", required=False)],
            "business_type": [
                ChoiceValidator("business_type", Customer.BUSINESS_TYPE, required=True)
            ],
            "company_type": [
                ChoiceValidator("company_type", Customer.COMPANY_TYPE, required=False)
            ],
            "gstin_number": [
                UniqueValidator(
                    "gstin_number", self.seen_gstin_numbers, required=False
                ),
                StringValidator("gstin_number", max_length=15, required=False),
            ],
            "pan_number": [
                UniqueValidator("pan_number", self.seen_pan_numbers, required=False),
                StringValidator("pan_number", max_length=10, required=False),
            ],
            "udyam_no": [
                UniqueValidator("udyam_no", self.seen_udyam_nos, required=False),
            ],
            "licence_no": [
                UniqueValidator("licence_no", self.seen_licence_nos, required=False),
            ],
            "delivery_days": [
                StringValidator("delivery_days", max_length=10, required=False)
            ],
            "credit_limit": [
                StringValidator("credit_limit", max_length=20, required=False)
            ],
            "due_days": [StringValidator("due_days", max_length=10, required=False)],
            "customer_balance": [
                ChoiceValidator(
                    "customer_balance", Customer.CUSTOMER_BALANCE, required=False
                )
            ],
        }

    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.

        Args:
            row_data: Raw row data from file

        Returns:
            Transformed data dictionary
        """
        field_mapping = self.get_field_mapping()
        transformed = {}

        related_fields = [
            "contact_person_name",
            "contact_person_designation",
            "contact_person_mobile_number",
            "contact_person_email",
            "bank_name",
            "bank_account_number",
            "bank_ifsc_code",
            "bank_branch_address",
            "beneficiary_swift_code",
            "bank_ad_code",
        ]
        for rf in related_fields:
            transformed[rf] = None

        numeric_string_fields = {
            "office_address_pin_code",
            "factory_address_pin_code",
            "phone_number",
            "fax_number",
            "contact_person_mobile_number",
        }

        row_data_lower = {
            k.strip().lower() if isinstance(k, str) else k: (k, v)
            for k, v in row_data.items()
        }

        for col_name, field_name in field_mapping.items():
            if col_name in row_data:
                value = row_data[col_name]
            else:
                col_name_lower = col_name.strip().lower()
                if col_name_lower in row_data_lower:
                    original_key, value = row_data_lower[col_name_lower]
                else:
                    value = None

            if value is None or (isinstance(value, str) and value.strip() == ""):
                continue

            if field_name in numeric_string_fields and not isinstance(value, str):
                try:
                    int_val = int(float(value))
                    value = str(int_val)
                except (ValueError, TypeError):
                    value = str(value).strip()
            elif field_name in numeric_string_fields and isinstance(value, str):
                stripped = value.strip()
                if stripped.endswith(".0") and stripped[:-2].isdigit():
                    value = stripped[:-2]

            if field_name == "customer_name":
                transformed[field_name] = normalize_string(value).strip()
            elif field_name == "customer_type":
                if value:
                    customer_type_name = normalize_string(value).strip()
                    customer_type_name_lower = customer_type_name.lower()

                    if customer_type_name_lower in self.customer_type_cache:
                        transformed[field_name] = self.customer_type_cache[
                            customer_type_name_lower
                        ]
                        logger.debug(
                            f"Found CustomerType '{customer_type_name}' in cache"
                        )
                    else:
                        try:
                            customer_type = CustomerType.objects.filter(
                                name__iexact=customer_type_name, deleted=False
                            ).first()

                            if not customer_type:
                                customer_type = CustomerType.objects.filter(
                                    name__icontains=customer_type_name, deleted=False
                                ).first()

                            if customer_type:
                                self.customer_type_cache[customer_type_name_lower] = (
                                    customer_type
                                )
                                transformed[field_name] = customer_type
                                logger.info(
                                    f"Found CustomerType '{customer_type_name}' -> ID: {customer_type.id}, Name: '{customer_type.name}'"
                                )
                            else:
                                logger.warning(
                                    f"CustomerType with name '{customer_type_name}' not found. Available types: {list(CustomerType.objects.filter(deleted=False).values_list('name', flat=True))}"
                                )
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(
                                f"Error looking up CustomerType '{customer_type_name}': {str(e)}",
                                exc_info=True,
                            )
                            transformed[field_name] = None
            elif (
                field_name == "sales_executive"
                or field_name == "sales_executive_assistant"
            ):
                if value:
                    search_value = normalize_string(value).strip()
                    search_value_lower = search_value.lower()

                    if search_value_lower in self.user_cache:
                        cached_user = self.user_cache[search_value_lower]
                        transformed[field_name] = cached_user
                        logger.debug(
                            f"Found User for '{search_value}' in cache: {cached_user.username} ({cached_user.first_name} {cached_user.last_name})"
                        )
                    else:
                        try:
                            user = None

                            user = User.objects.filter(
                                username__iexact=search_value
                            ).first()
                            if user:
                                logger.debug(
                                    f"Found User by username '{search_value}': {user.username}"
                                )

                            if not user:
                                name_parts = search_value.split()
                                if len(name_parts) >= 2:
                                    first_name = name_parts[0].strip()
                                    last_name = " ".join(name_parts[1:]).strip()
                                    user = User.objects.filter(
                                        first_name__iexact=first_name,
                                        last_name__iexact=last_name,
                                    ).first()
                                    if user:
                                        logger.debug(
                                            f"Found User by full name '{first_name} {last_name}': {user.username}"
                                        )

                            if not user:
                                name_parts = search_value.split()
                                if len(name_parts) >= 1:
                                    first_name = name_parts[0].strip()
                                    user = User.objects.filter(
                                        first_name__iexact=first_name
                                    ).first()
                                    if user:
                                        logger.debug(
                                            f"Found User by first name '{first_name}': {user.username}"
                                        )

                            if not user and "@" in search_value:
                                user = User.objects.filter(
                                    email__iexact=search_value
                                ).first()
                                if user:
                                    logger.debug(
                                        f"Found User by email '{search_value}': {user.username}"
                                    )

                            if user:
                                self.user_cache[search_value_lower] = user
                                transformed[field_name] = user
                                logger.info(
                                    f"Found User for '{search_value}' -> ID: {user.id}, Username: '{user.username}', Name: '{user.first_name} {user.last_name}'"
                                )
                            else:
                                available_users = User.objects.all()[:5].values_list(
                                    "username", "first_name", "last_name"
                                )
                                logger.warning(
                                    f"User not found for '{search_value}' (tried: username, full name, first name, email). Sample users: {list(available_users)}"
                                )
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(
                                f"Error looking up User '{search_value}': {str(e)}",
                                exc_info=True,
                            )
                            transformed[field_name] = None
            elif field_name == "business_type":
                transformed[field_name] = normalize_choice(
                    value, Customer.BUSINESS_TYPE
                )
            elif field_name == "company_type":
                transformed[field_name] = normalize_choice(value, Customer.COMPANY_TYPE)
            elif field_name == "customer_balance":
                transformed[field_name] = normalize_choice(
                    value, Customer.CUSTOMER_BALANCE
                )
            elif field_name == "is_company_visible_on_documents":
                if isinstance(value, bool):
                    transformed[field_name] = value
                elif isinstance(value, str):
                    transformed[field_name] = value.lower().strip() in (
                        "true",
                        "1",
                        "yes",
                        "on",
                    )
                else:
                    transformed[field_name] = bool(value)
            elif field_name in ["delivery_days", "due_days"]:
                try:
                    transformed[field_name] = int(float(str(value))) if value else None
                except (ValueError, TypeError):
                    transformed[field_name] = None
            elif field_name == "credit_limit":
                try:
                    transformed[field_name] = float(str(value)) if value else None
                except (ValueError, TypeError):
                    transformed[field_name] = None
            elif field_name in related_fields:
                transformed[field_name] = normalize_string(value) if value else None
            else:
                transformed[field_name] = normalize_string(value) if value else None

        business_type = transformed.get("business_type", "INDIAN")
        if business_type == "INDIAN":
            transformed["beneficiary_agent_code"] = None
            transformed["import_export_code"] = None
        else:
            transformed["gstin_number"] = None
            transformed["gst_type"] = None
            transformed["pan_number"] = None
            transformed["udyam_no"] = None
            transformed["applicable_gst"] = None

        company_type = transformed.get("company_type", "customer")
        if company_type == "vendor":
            transformed["customer_type"] = None
            transformed["sales_executive"] = None
            transformed["sales_executive_assistant"] = None
            transformed["delivery_days"] = None

        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def validate_all_rows(self) -> tuple[int, int]:
        """
        Override to track row numbers in validated_data for error reporting.
        When a row fails only due to "duplicated in the import file" and the row is an exact
        duplicate of an already-accepted row, skip it and do NOT add to row_errors (no duplicate in row_errors).
        """
        if not self.parser:
            logger.warning("Parser not initialized")
            return 0, 0

        rows = self.parser.get_rows()
        logger.info(f"Parsed {len(rows)} rows from file")

        if not rows:
            logger.warning("No rows found in parsed file")
            return 0, 0

        valid_count = 0
        error_count = 0
        self._skipped_duplicate_count = 0
        seen_raw_signatures = set()

        for idx, row_data in enumerate(rows, start=1):
            try:
                is_valid, errors = self.validate_row(row_data, idx)

                if is_valid:
                    try:
                        transformed_data = self.transform_row_data(row_data)
                        transformed_data["_row_number"] = idx
                        self.validated_data.append(transformed_data)
                        seen_raw_signatures.add(self._make_raw_row_signature(row_data))
                        valid_count += 1
                        logger.debug(
                            f"Row {idx} validated and transformed successfully"
                        )
                    except Exception as e:
                        logger.error(f"Error transforming row {idx}: {str(e)}")
                        self._add_error_to_log(
                            row_number=idx,
                            error_type="validation",
                            field_name=None,
                            error_message=f"Data transformation error: {str(e)}",
                            raw_data=row_data,
                        )
                        error_count += 1
                else:
                    raw_sig = self._make_raw_row_signature(row_data)
                    if (
                        self._errors_are_only_duplicated_in_file(errors)
                        and raw_sig in seen_raw_signatures
                    ):
                        logger.info(
                            f"Row {idx}: Exact duplicate row -> counting as skipped only (not in error_count or row_errors)"
                        )
                        self._skipped_duplicate_count += 1
                        continue
                    logger.debug(f"Row {idx} has {len(errors)} validation errors")
                    for error in errors:
                        self._add_error_to_log(
                            row_number=idx,
                            error_type="validation",
                            field_name=error.get("field"),
                            error_message=error.get("message"),
                            raw_data=row_data,
                        )
                    error_count += 1
            except Exception as e:
                logger.error(f"Error validating row {idx}: {str(e)}", exc_info=True)
                self._add_error_to_log(
                    row_number=idx,
                    error_type="unknown",
                    field_name=None,
                    error_message=f"Validation error: {str(e)}",
                    raw_data=row_data,
                )
                error_count += 1

        logger.info(
            f"Validation complete: {valid_count} valid, {error_count} errors, {getattr(self, '_skipped_duplicate_count', 0)} skipped (exact duplicates)"
        )
        return valid_count, error_count

    def create_model_instance(self, validated_data: Dict) -> Customer:
        """
        Create Customer model instance from validated data.
        Note: Related data (ContactPerson, BankingDetails) is handled in save_data override.

        Args:
            validated_data: Validated and transformed data

        Returns:
            Customer instance (not saved)
        """
        validated_data.pop("amount", None)

        return Customer(**validated_data)

    def _is_exact_duplicate(self, existing_customer: Customer, new_data: Dict) -> bool:
        """
        Check if the existing customer record matches the new data exactly.
        Compares all customer fields that exist in both the model and new_data.

        Args:
            existing_customer: Existing Customer instance
            new_data: New data dictionary to compare (should already have audit fields removed)

        Returns:
            True if records are identical, False otherwise
        """
        exclude_fields = {
            "id",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
            "deleted",
            "deleted_at",
            "deleted_by",
        }

        try:
            model_field_names = set()
            for f in Customer._meta.get_fields():
                if not f.auto_created:
                    model_field_names.add(f.name)

            fields_to_compare = (
                set(new_data.keys()) & model_field_names - exclude_fields
            )

            if not fields_to_compare:
                logger.warning(
                    f"No fields to compare in duplicate check. Model fields: {model_field_names}, New data keys: {set(new_data.keys())}"
                )
                return False

            differences = []

            for field_name in sorted(fields_to_compare):
                try:
                    field = Customer._meta.get_field(field_name)
                except Exception as e:
                    logger.debug(
                        f"Skipping field {field_name} (not in model): {str(e)}"
                    )
                    continue

                existing_value = getattr(existing_customer, field_name, None)

                new_value = new_data.get(field_name)

                existing_normalized = None
                if existing_value is not None:
                    if isinstance(existing_value, str):
                        existing_normalized = (
                            existing_value.strip() if existing_value.strip() else None
                        )
                    else:
                        existing_normalized = existing_value
                else:
                    existing_normalized = None

                new_normalized = None
                if new_value is not None:
                    if isinstance(new_value, str):
                        new_normalized = (
                            new_value.strip() if new_value.strip() else None
                        )
                    else:
                        new_normalized = new_value
                else:
                    new_normalized = None

                if hasattr(field, "related_model"):
                    existing_id = (
                        existing_normalized.id if existing_normalized else None
                    )
                    if hasattr(new_normalized, "id"):
                        new_id = new_normalized.id
                    elif isinstance(new_normalized, (int, str)) and new_normalized:
                        try:
                            new_id = int(new_normalized)
                        except (ValueError, TypeError):
                            new_id = None
                    else:
                        new_id = None

                    if existing_id != new_id:
                        differences.append(
                            f"{field_name}: existing_id={existing_id}, new_id={new_id}"
                        )
                        logger.debug(
                            f"Field {field_name} differs: existing_id={existing_id}, new_id={new_id}"
                        )
                else:
                    are_equal = False

                    if isinstance(existing_normalized, (float, int)) and isinstance(
                        new_normalized, (float, int)
                    ):
                        are_equal = (
                            abs(float(existing_normalized) - float(new_normalized))
                            < 0.01
                        )
                    elif isinstance(existing_normalized, str) and isinstance(
                        new_normalized, str
                    ):
                        are_equal = (
                            existing_normalized.lower() == new_normalized.lower()
                        )
                    elif isinstance(existing_normalized, bool) and isinstance(
                        new_normalized, bool
                    ):
                        are_equal = existing_normalized == new_normalized
                    elif existing_normalized is None and new_normalized is None:
                        are_equal = True
                    else:
                        are_equal = existing_normalized == new_normalized

                    if not are_equal:
                        differences.append(
                            f"{field_name}: '{existing_normalized}' != '{new_normalized}' (types: {type(existing_normalized).__name__} vs {type(new_normalized).__name__})"
                        )
                        logger.debug(
                            f"Field {field_name} differs: '{existing_normalized}' != '{new_normalized}' (types: {type(existing_normalized).__name__} vs {type(new_normalized).__name__})"
                        )

            if differences:
                logger.info(
                    f"Customer '{existing_customer.customer_name}' (ID: {existing_customer.id}) has {len(differences)} differences: {', '.join(differences[:5])}"
                )
                return False

            logger.info(
                f"Customer '{existing_customer.customer_name}' (ID: {existing_customer.id}) is an exact duplicate - all {len(fields_to_compare)} fields match"
            )
            return True
        except Exception as e:
            logger.error(f"Error in _is_exact_duplicate: {str(e)}", exc_info=True)
            return False

    def _is_exact_duplicate_v2(
        self, existing_customer: Customer, new_data: Dict
    ) -> bool:
        """
        Alternative duplicate check using model_to_dict for more reliable comparison.
        This method converts the existing customer to a dict and compares field by field.

        Args:
            existing_customer: Existing Customer instance
            new_data: New data dictionary to compare (should already have audit fields removed)

        Returns:
            True if records are identical, False otherwise
        """
        exclude_fields = {
            "id",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
            "deleted",
            "deleted_at",
            "deleted_by",
        }

        try:
            existing_dict = model_to_dict(existing_customer, exclude=exclude_fields)

            def normalize_value(value):
                """Normalize a value for comparison"""
                if value is None:
                    return None
                if isinstance(value, str):
                    normalized = value.strip()
                    return normalized.lower() if normalized else None
                if hasattr(value, "id"):
                    return value.id
                if hasattr(value, "__float__"):
                    return float(value)
                return value

            differences = []
            fields_compared = 0

            for field_name, new_value in new_data.items():
                if field_name in exclude_fields:
                    continue

                fields_compared += 1
                existing_value = existing_dict.get(field_name)

                existing_norm = normalize_value(existing_value)
                new_norm = normalize_value(new_value)

                if existing_norm != new_norm:
                    differences.append(
                        f"{field_name}: '{existing_norm}' != '{new_norm}'"
                    )
                    logger.debug(
                        f"Field {field_name} differs: existing='{existing_norm}', new='{new_norm}'"
                    )

            if differences:
                logger.info(
                    f"Customer '{existing_customer.customer_name}' (ID: {existing_customer.id}) has {len(differences)} differences out of {fields_compared} fields compared:"
                )
                for diff in differences[:10]:
                    logger.info(f"  - {diff}")
                if len(differences) > 10:
                    logger.info(f"  ... and {len(differences) - 10} more differences")
                return False

            logger.info(
                f"Customer '{existing_customer.customer_name}' (ID: {existing_customer.id}) is an exact duplicate - all {fields_compared} fields match"
            )
            return True

        except Exception as e:
            logger.error(f"Error in _is_exact_duplicate_v2: {str(e)}", exc_info=True)
            return False

    def _make_row_signature(self, row_data: Dict) -> tuple:
        """
        Build a hashable signature of row data for duplicate-in-CSV detection.
        Rows with the same signature are treated as "whole row same" and skipped (not in row_errors).
        """

        def _norm(v):
            if v is None:
                return "__None__"
            if isinstance(v, str):
                return (v.strip().lower() or "") or "__None__"
            if hasattr(v, "id"):
                return ("fk", v.id)
            if isinstance(v, (int, float, bool)):
                return v
            return str(v)

        try:
            return tuple(sorted((k, _norm(v)) for k, v in row_data.items()))
        except Exception:
            return (id(row_data),)

    def _make_raw_row_signature(self, row_data: Dict) -> tuple:
        """
        Build a hashable signature from raw parser row (CSV/Excel column names -> values).
        Used in validation to detect exact duplicate rows so we skip them without adding to row_errors.
        """

        def _norm_raw(v):
            if v is None:
                return ""
            s = str(v).strip().lower()
            return s if s else ""

        try:
            return tuple(
                sorted(
                    (str(k).strip().lower(), _norm_raw(v)) for k, v in row_data.items()
                )
            )
        except Exception:
            return (id(row_data),)

    def _errors_are_only_duplicated_in_file(self, errors: List[Dict]) -> bool:
        """True if every error message is 'duplicated in the import file'."""
        if not errors:
            return False
        dup_msg = "duplicated in the import file"
        return all(dup_msg in (e.get("message") or "") for e in errors)

    def import_data(self) -> Dict:
        """
        Override to include exact-duplicate rows in 'skipped' only (not in error_count or row_errors).
        """
        result = super().import_data()
        skipped_duplicates = getattr(self, "_skipped_duplicate_count", 0)
        if skipped_duplicates:
            result["skipped"] = result.get("skipped", 0) + skipped_duplicates
        return result

    def save_data(self) -> tuple[int, int, int, int]:
        """
        Override save_data to handle related ContactPerson and BankingDetails creation.
        Also tracks row-level errors for detailed reporting.

        Returns:
            Tuple of (inserted_count, updated_count, skipped_count, failed_count)
        """
        if self.dry_run:
            return len(self.validated_data), 0, 0, 0

        if not self.validated_data:
            return 0, 0, 0, 0

        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        seen_row_signatures = set()

        for idx, data in enumerate(self.validated_data):
            row_number = data.get("_row_number", idx + 2)

            data_for_sig = {k: v for k, v in data.items() if k != "_row_number"}
            row_sig = self._make_row_signature(data_for_sig)
            if row_sig in seen_row_signatures:
                logger.info(
                    f"Row {row_number}: Skipping duplicate row (same as a previous row in CSV)"
                )
                skipped_count += 1
                data.pop("_row_number", None)
                continue
            seen_row_signatures.add(row_sig)
            data.pop("_row_number", None)

            data_copy = data.copy()

            contact_person_data = {
                "contact_person_name": data_copy.pop("contact_person_name", None),
                "contact_person_designation": data_copy.pop(
                    "contact_person_designation", None
                ),
                "contact_person_mobile_number": data_copy.pop(
                    "contact_person_mobile_number", None
                ),
                "contact_person_email": data_copy.pop("contact_person_email", None),
            }

            banking_detail_data = {
                "bank_name": data_copy.pop("bank_name", None),
                "bank_account_number": data_copy.pop("bank_account_number", None),
                "bank_ifsc_code": data_copy.pop("bank_ifsc_code", None),
                "bank_branch_address": data_copy.pop("bank_branch_address", None),
                "beneficiary_swift_code": data_copy.pop("beneficiary_swift_code", None),
                "bank_ad_code": data_copy.pop("bank_ad_code", None),
            }

            try:
                with transaction.atomic():
                    customer_name = data_copy.get("customer_name")
                    validation_errors = []

                    gstin_number = data_copy.get("gstin_number")
                    if gstin_number:
                        existing_by_gstin = (
                            Customer.objects.filter(
                                gstin_number__iexact=gstin_number, deleted=False
                            )
                            .exclude(
                                customer_name__iexact=(
                                    customer_name if customer_name else None
                                )
                            )
                            .first()
                        )
                        if existing_by_gstin:
                            validation_errors.append(
                                f"GSTIN number '{gstin_number}' already exists"
                            )

                    pan_number = data_copy.get("pan_number")
                    if pan_number:
                        existing_by_pan = (
                            Customer.objects.filter(
                                pan_number__iexact=pan_number, deleted=False
                            )
                            .exclude(
                                customer_name__iexact=(
                                    customer_name if customer_name else None
                                )
                            )
                            .first()
                        )
                        if existing_by_pan:
                            validation_errors.append(
                                f"PAN number '{pan_number}' already exists"
                            )

                    udyam_no = data_copy.get("udyam_no")
                    if udyam_no:
                        existing_by_udyam = (
                            Customer.objects.filter(
                                udyam_no__iexact=udyam_no, deleted=False
                            )
                            .exclude(
                                customer_name__iexact=(
                                    customer_name if customer_name else None
                                )
                            )
                            .first()
                        )
                        if existing_by_udyam:
                            validation_errors.append(
                                f"Udyam No '{udyam_no}' already exists"
                            )

                    licence_no = data_copy.get("licence_no")
                    if licence_no:
                        existing_by_licence = (
                            Customer.objects.filter(
                                licence_no__iexact=licence_no, deleted=False
                            )
                            .exclude(
                                customer_name__iexact=(
                                    customer_name if customer_name else None
                                )
                            )
                            .first()
                        )
                        if existing_by_licence:
                            validation_errors.append(
                                f"Licence No '{licence_no}' already exists"
                            )

                    if validation_errors:
                        error_message = "; ".join(validation_errors)
                        self._add_error_to_log(
                            row_number=row_number,
                            error_type="validation",
                            field_name="customer",
                            error_message=error_message,
                            raw_data=data_copy,
                        )
                        logger.warning(f"Row {row_number}: {error_message}")
                        skipped_count += 1
                        continue

                    existing_customer = None
                    if customer_name:
                        existing_customer = Customer.objects.filter(
                            customer_name__iexact=customer_name, deleted=False
                        ).first()

                    if existing_customer:
                        audit_fields = [
                            "id",
                            "created_by",
                            "created_at",
                            "updated_by",
                            "updated_at",
                            "deleted",
                            "deleted_at",
                            "deleted_by",
                        ]
                        comparison_data = {
                            k: v for k, v in data_copy.items() if k not in audit_fields
                        }

                        logger.info(
                            f"Row {row_number}: Found existing customer '{customer_name}' (ID: {existing_customer.id}), checking for duplicates..."
                        )

                        is_duplicate = self._is_exact_duplicate_v2(
                            existing_customer, comparison_data
                        )

                        if is_duplicate:
                            logger.info(
                                f"Row {row_number}: ✓ Skipping exact duplicate customer '{customer_name}' (ID: {existing_customer.id})"
                            )
                            customer = existing_customer
                        else:
                            logger.info(
                                f"Row {row_number}: ✗ Customer '{customer_name}' (ID: {existing_customer.id}) has differences, updating..."
                            )

                            fk_fields = {
                                "customer_type": data_copy.get("customer_type"),
                                "sales_executive": data_copy.get("sales_executive"),
                                "sales_executive_assistant": data_copy.get(
                                    "sales_executive_assistant"
                                ),
                            }
                            for fk_name, fk_value in fk_fields.items():
                                if fk_value:
                                    if hasattr(fk_value, "id"):
                                        logger.info(
                                            f"Row {row_number}: Updating {fk_name} FK: ID={fk_value.id}, Name={getattr(fk_value, 'name', getattr(fk_value, 'username', 'N/A'))}"
                                        )
                                    else:
                                        logger.warning(
                                            f"Row {row_number}: {fk_name} is not a FK object: {type(fk_value)} = {fk_value}"
                                        )

                            for key, value in data_copy.items():
                                if key not in ["id", "created_by", "created_at"]:
                                    setattr(existing_customer, key, value)
                            existing_customer.updated_by = self.user
                            existing_customer.save()
                            customer = existing_customer
                            updated_count += 1
                            logger.info(
                                f"Row {row_number}: Updated customer '{customer_name}' (ID: {existing_customer.id})"
                            )
                    else:
                        fk_fields = {
                            "customer_type": data_copy.get("customer_type"),
                            "sales_executive": data_copy.get("sales_executive"),
                            "sales_executive_assistant": data_copy.get(
                                "sales_executive_assistant"
                            ),
                        }
                        for fk_name, fk_value in fk_fields.items():
                            if fk_value:
                                if hasattr(fk_value, "id"):
                                    logger.info(
                                        f"Row {row_number}: {fk_name} FK object found: ID={fk_value.id}, Name={getattr(fk_value, 'name', getattr(fk_value, 'username', 'N/A'))}"
                                    )
                                else:
                                    logger.warning(
                                        f"Row {row_number}: {fk_name} is not a FK object: {type(fk_value)} = {fk_value}"
                                    )
                            else:
                                logger.debug(f"Row {row_number}: {fk_name} is None")

                        customer = Customer.objects.create(**data_copy)
                        inserted_count += 1
                        logger.info(
                            f"Row {row_number}: Created customer '{customer_name}' (ID: {customer.id})"
                        )

                    if contact_person_data.get("contact_person_mobile_number"):
                        try:
                            ContactPerson.objects.update_or_create(
                                customer=customer,
                                contact_person_mobile_number=contact_person_data[
                                    "contact_person_mobile_number"
                                ],
                                defaults={
                                    **contact_person_data,
                                    "created_by": self.user,
                                    "updated_by": self.user,
                                },
                            )
                            logger.info(
                                f"Row {row_number}: ContactPerson saved for customer '{customer_name}'"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Row {row_number}: Error creating ContactPerson: {str(e)}"
                            )
                            self._add_error_to_log(
                                row_number=row_number,
                                error_type="related_data",
                                field_name="contact_person",
                                error_message=f"Error creating ContactPerson: {str(e)}",
                                raw_data=contact_person_data,
                            )

                    if banking_detail_data.get("bank_account_number"):
                        try:
                            BankingDetails.objects.update_or_create(
                                customer=customer,
                                bank_account_number=banking_detail_data[
                                    "bank_account_number"
                                ],
                                defaults={
                                    **banking_detail_data,
                                    "created_by": self.user,
                                    "updated_by": self.user,
                                },
                            )
                            logger.info(
                                f"Row {row_number}: BankingDetails saved for customer '{customer_name}'"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Row {row_number}: Error creating BankingDetails: {str(e)}"
                            )
                            self._add_error_to_log(
                                row_number=row_number,
                                error_type="related_data",
                                field_name="banking_details",
                                error_message=f"Error creating BankingDetails: {str(e)}",
                                raw_data=banking_detail_data,
                            )

                    if existing_customer and is_duplicate if existing_customer else False:
                        skipped_count += 1

            except IntegrityError as e:
                error_msg = str(e)
                field_name = "unknown"
                if "customer_name" in error_msg.lower():
                    field_name = "customer_name"
                elif "gstin_number" in error_msg.lower():
                    field_name = "gstin_number"
                elif "pan_number" in error_msg.lower():
                    field_name = "pan_number"
                elif "udyam_no" in error_msg.lower():
                    field_name = "udyam_no"
                elif "licence_no" in error_msg.lower():
                    field_name = "licence_no"

                self._add_error_to_log(
                    row_number=row_number,
                    error_type="database",
                    field_name=field_name,
                    error_message=f"Database constraint violation: {error_msg}",
                    raw_data=data_copy,
                )
                logger.error(
                    f"Row {row_number}: IntegrityError - {error_msg}", exc_info=True
                )
                failed_count += 1
            except Exception as e:
                error_msg = str(e)
                self._add_error_to_log(
                    row_number=row_number,
                    error_type="unknown",
                    field_name=None,
                    error_message=f"Error saving customer: {error_msg}",
                    raw_data=data_copy,
                )
                logger.error(
                    f"Row {row_number}: Error saving customer: {error_msg}",
                    exc_info=True,
                )
                failed_count += 1

        return inserted_count, updated_count, skipped_count, failed_count

    def _add_error_to_log(
        self, row_number, error_type, field_name, error_message, raw_data
    ):
        """Helper method to add error to import log"""
        if self.import_log:
            try:
                from imports.models import ImportErrorRow

                ImportErrorRow.objects.create(
                    import_log=self.import_log,
                    row_number=row_number,
                    error_type=error_type,
                    field_name=field_name,
                    error_message=error_message,
                    raw_data=raw_data if isinstance(raw_data, dict) else {},
                )
            except Exception as e:
                logger.error(f"Error creating ImportErrorRow: {str(e)}", exc_info=True)