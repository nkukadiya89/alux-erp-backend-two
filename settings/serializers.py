from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator, URLValidator
from rest_framework import serializers

from settings.models import (
    CompanySettings,
    FinancialSettings,
    NotificationSettings,
    TaxComplianceSettings,
    TermAndConditionSettings,
    ProductionSettings,
)
from user.models import User
from user.serializers import UserQuickSerializer


class CompanySettingsSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    company_logo = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = CompanySettings
        fields = [
            "id",
            "company_name",
            "legal_name",
            "company_logo",
            "website",
            "color",
            "email",
            "phone",
            "landline",
            "office_address",
            "factory_address",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "deleted", "company_logo"]

    def validate_company_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Company name is required.")
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Company name must be at least 2 characters."
            )
        return value.strip()

    def validate_email(self, value):
        if value:
            validator = EmailValidator()
            try:
                validator(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid email format.")
        return value

    def validate_website(self, value):
        if value:
            validator = URLValidator()
            try:
                validator(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid website URL format.")
        return value

    def validate_phone(self, value):
        if value:
            cleaned = "".join(filter(str.isdigit, value))
            if len(cleaned) < 10:
                raise serializers.ValidationError(
                    "Phone number must be at least 10 digits."
                )
        return value


class NotificationSettingsSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    alert_emails = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False
    )
    alert_emails_detail = UserQuickSerializer(
        source="alert_emails", many=True, read_only=True
    )

    class Meta:
        model = NotificationSettings
        fields = [
            "id",
            "email_notifications",
            "push_notifications",
            "smtp_server",
            "system_email",
            "daily_summary",
            "alert_emails",
            "alert_emails_detail",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "deleted"]

    def validate_system_email(self, value):
        if value:
            validator = EmailValidator()
            try:
                validator(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid email format.")
        return value

    def validate(self, attrs):
        if attrs.get("email_notifications") and not attrs.get("system_email"):
            raise serializers.ValidationError(
                {
                    "system_email": "System email is required when email notifications are enabled."
                }
            )
        return attrs


class TaxComplianceSettingsSerializer(serializers.ModelSerializer):
    compliance_document = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = TaxComplianceSettings
        fields = [
            "id",
            "tax_registration_no",
            "igst",
            "cgst",
            "sgst",
            "tax_rounding_method",
            "tax_report_email",
            "compliance_document",
            "pan_number",
        ]
        read_only_fields = ["id", "compliance_document"]

    def validate_tax_registration_no(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Tax registration number is required.")
        return value.strip()

    def validate_tax_report_email(self, value):
        if value:
            validator = EmailValidator()
            try:
                validator(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid email format.")
        return value


class FinancialSettingsSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)

    class Meta:
        model = FinancialSettings
        fields = [
            "id",
            "fiscal_year_start",
            "bank_name",
            "account_number",
            "ifsc_code",
            "bank_address",
            "payment_terms",
            "invoice_prefix",
            "rounding_precision",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "deleted"]

    def validate_invoice_prefix(self, value):
        if value:
            if len(value) > 10:
                raise serializers.ValidationError(
                    "Invoice prefix must not exceed 10 characters."
                )
            if not value.replace("-", "").replace("_", "").isalnum():
                raise serializers.ValidationError(
                    "Invoice prefix can only contain letters, numbers, hyphens, and underscores."
                )
        return value


class TermAndConditionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermAndConditionSettings
        fields = [
            "id",
            "die_terms_and_conditions",
            "quotation_terms_and_conditions",
            "proforma_terms_and_conditions",
            "work_order_terms_and_conditions",
        ]

class ProductionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionSettings
        fields = [
            "id",
            "work_order_creation_mode",
            "nalco_approved_by",
        ]

class ProductionSettingsListSerializer(serializers.ModelSerializer):
    nalco_approved_by = UserQuickSerializer(many=True, read_only=True)
    class Meta:
        model = ProductionSettings
        fields = [
            "id",
            "work_order_creation_mode",
            "nalco_approved_by"
        ]