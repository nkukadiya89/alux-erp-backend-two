import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from utils.aws_file_upload import delete_uploaded_file, upload_doc_file

logger = logging.getLogger("file")


class BaseModule(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        user = kwargs.pop("user", None)
        if is_new:

            self.updated_at = None
            self.updated_by = None
            if user and not self.created_by:
                self.created_by = user
        else:
            self.updated_at = timezone.now()
            if user:
                self.updated_by = user

        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        """
        Soft delete the record by setting deleted=True, deleted_at, and deleted_by.
        This ensures audit trail is maintained.
        """
        self.deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        models.Model.save(self, update_fields=["deleted", "deleted_at", "deleted_by"])

        return (1, {self.__class__.__name__: [self.pk]})


class CompanySettings(BaseModule):
    company_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True, null=True)
    company_logo = models.CharField(max_length=255, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    landline = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    office_address = models.TextField(blank=True, null=True)
    factory_address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.company_name

    def upload_doc(self, doc_dict: dict = {}):
        error_list = []
        logger.info("Document upload initiated with the following files: %s", doc_dict)

        allowed_types_mapping = {"company_logo": [".png", ".svg"]}

        max_file_size = 2 * 1024 * 1024

        for attr, doc in doc_dict.items():
            if doc is not None:
                logger.info(f"Processing file for {attr}: {doc.name}")
                file_extension = os.path.splitext(doc.name)[1].lower()
                allowed_types = allowed_types_mapping.get(attr, [])

                if file_extension not in allowed_types:
                    raise ValidationError(
                        {
                            attr: f"Invalid file type {file_extension} for {attr}. Allowed: {', '.join(allowed_types)}"
                        }
                    )

                if doc.size > max_file_size:
                    raise ValidationError(
                        {
                            attr: f"File size too large for {attr}. Maximum allowed size is 2 MB."
                        }
                    )

                current_value = getattr(self, attr, None)

                try:
                    if current_value:
                        delete_uploaded_file(current_value)

                    new_value, _ = upload_doc_file(
                        doc, allowed_types, "CompanySettings/", self.id, None
                    )

                    if new_value:
                        setattr(self, attr, new_value)
                    else:
                        error_list.append(f"Failed to upload {attr}")

                except Exception as e:
                    error_list.append(f"Error processing {attr}: {e}")
                    logger.error(f"Error processing {attr}: {e}")
            else:
                logger.warning(f"No file provided for {attr}, skipping upload.")

        self.save()

        if error_list:
            raise ValidationError({"upload_errors": error_list})


class NotificationSettings(BaseModule):
    email_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=False)
    smtp_server = models.CharField(max_length=255, blank=True, null=True)
    system_email = models.CharField(max_length=255, blank=True, null=True)
    daily_summary = models.BooleanField(default=False)
    alert_emails = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="notification_alert_emails",
        blank=True,
    )

    def __str__(self):
        return f"Notification Settings (ID: {self.system_email})"


class TaxComplianceSettings(models.Model):
    TAX_ROUNDING_CHOICES = [
        ("Per_line", "Per_line"),
        ("On_total", "On_total"),
    ]
    pan_number = models.CharField(max_length=100, blank=True, null=True)
    tax_registration_no = models.CharField(max_length=100, null=True, blank=True)
    igst = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    cgst = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sgst = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tax_rounding_method = models.CharField(
        max_length=20, choices=TAX_ROUNDING_CHOICES, default="On_total"
    )
    tax_report_email = models.CharField(max_length=255, blank=True, null=True)
    compliance_document = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Tax Compliance Settings (Reg No: {self.tax_registration_no})"

    def upload_doc(self, doc_dict: dict = {}):
        error_list = []
        logger.info("Document upload initiated with the following files: %s", doc_dict)

        allowed_types_mapping = {
            "compliance_document": [".pdf", ".jpg", ".jpeg", ".png"],
        }

        max_file_size = 2 * 1024 * 1024

        for attr, doc in doc_dict.items():
            if doc is not None:
                logger.info(f"Processing file for {attr}: {doc.name}")
                file_extension = os.path.splitext(doc.name)[1].lower()
                allowed_types = allowed_types_mapping.get(attr, [])

                if file_extension not in allowed_types:
                    raise ValidationError(
                        {
                            attr: f"Invalid file type {file_extension} for {attr}. Allowed: {', '.join(allowed_types)}"
                        }
                    )

                if doc.size > max_file_size:
                    raise ValidationError(
                        {
                            attr: f"File size too large for {attr}. Maximum allowed size is 2 MB."
                        }
                    )

                current_value = getattr(self, attr, None)

                try:
                    if current_value:
                        delete_uploaded_file(current_value)

                    new_value, _ = upload_doc_file(
                        doc, allowed_types, "TaxComplianceSettings/", self.id, None
                    )

                    if new_value:
                        setattr(self, attr, new_value)
                    else:
                        error_list.append(f"Failed to upload {attr}")

                except Exception as e:
                    error_list.append(f"Error processing {attr}: {e}")
                    logger.error(f"Error processing {attr}: {e}")
            else:
                logger.warning(f"No file provided for {attr}, skipping upload.")

        self.save()

        if error_list:
            raise ValidationError({"upload_errors": error_list})


class FinancialSettings(BaseModule):
    FISCAL_YEAR_CHOICES = [
        ("April-March", "April-March"),
        ("July-June", "July-June"),
        ("October-September", "October-September"),
        ("January-December", "January-December"),
    ]
    PAYMENT_TERMS_CHOICES = [
        ("7", "7"),
        ("15", "15"),
        ("30", "30"),
    ]
    ROUNDING_PRECISION_CHOICES = [
        ("1", "1"),
        ("0.01", "0.01"),
        ("0.05", "0.05"),
    ]
    fiscal_year_start = models.CharField(
        max_length=30, choices=FISCAL_YEAR_CHOICES, default="April-March"
    )
    payment_terms = models.CharField(
        max_length=20, choices=PAYMENT_TERMS_CHOICES, default="30"
    )
    invoice_prefix = models.CharField(
        max_length=20, blank=True, null=True, default="INV-"
    )
    rounding_precision = models.CharField(
        max_length=10, choices=ROUNDING_PRECISION_CHOICES, default="0.01"
    )
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    ifsc_code = models.CharField(max_length=20, null=True, blank=True)
    bank_address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Financial Settings (Fiscal Year: {self.fiscal_year_start})"


class TermAndConditionSettings(BaseModule):
    die_terms_and_conditions = models.TextField(blank=True, null=True)
    quotation_terms_and_conditions = models.TextField(blank=True, null=True)
    proforma_terms_and_conditions = models.TextField(blank=True, null=True)
    work_order_terms_and_conditions = models.TextField(blank=True, null=True)

    def __str__(self):
        return "Terms and Conditions Settings"


class ProductionSettings(BaseModule):
    CREATION_MODE_CHOICES = (
        ("crm_based", "crm_based"),
        ("sales_order_based", "sales_order_based"),
        ("direct_work_order", "direct_work_order")
    )
    work_order_creation_mode = models.CharField(
        max_length=30,
        choices=CREATION_MODE_CHOICES,
        default="crm_based"
    )
    nalco_approved_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="nalco_approved_by",
        blank=True,
    )

    def __str__(self):
        return "Production Settings"
