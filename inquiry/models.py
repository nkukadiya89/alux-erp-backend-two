import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

from common.models import JobWorkType
from product.models import Alloy, Temper
from utils.aws_file_upload import delete_uploaded_file, upload_doc_file

logger = logging.getLogger("file")


class Inquiry(models.Model):
    INQUIRY_SOURCE_CHOICE = (
        ("Open_Form", "Open_Form"),
        ("Whatsapp", "Whatsapp"),
        ("Email", "Email"),
        ("Call", "Call"),
        ("Expo", "Expo"),
        ("Reference", "Reference"),
        ("Visit", "Visit"),
        ("Agents", "Agents"),
        ("Marketing_Person", "Marketing_Person")
    )

    INQUIRY_STATUS_CHOICE = (
        ("Pending", "Pending"),
        ("Assigned", "Assigned"),
        ("Feasible", "Feasible"),
        ("Regretted", "Regretted"),
        ("Quotation", "Quotation"),
        ("SalesOrder", "SalesOrder"),
        ("Quotation_Sent", "Quotation_Sent"),
        ("SalesOrder_Generated", "SalesOrder_Generated"),
    )
    inquiry_number = models.CharField(max_length=20, unique=True)
    inquiry_date = models.DateTimeField(default=now, db_index=True)
    customer_name = models.CharField(max_length=100, db_index=True)
    contact_persons = models.JSONField(default=list)
    initial_requirement = models.CharField(max_length=250)
    annual_requirement = models.CharField(max_length=250)
    inquiry_source = models.CharField(
        max_length=100, default="Open_Form", choices=INQUIRY_SOURCE_CHOICE
    )
    source_attachment = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(
        max_length=100, default="Pending", choices=INQUIRY_STATUS_CHOICE, db_index=True
    )
    regret_reason = models.CharField(max_length=100, null=True, blank=True)
    feasiblity_attachment = models.CharField(max_length=250, null=True, blank=True)
    feasiblity_description = models.TextField(null=True, blank=True)
    inquiry_source = models.CharField(
        max_length=100, default="Open_Form", choices=INQUIRY_SOURCE_CHOICE
    )
    source_attachment = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(
        max_length=100, default="Pending", choices=INQUIRY_STATUS_CHOICE, db_index=True
    )
    regret_reason = models.CharField(max_length=100, null=True, blank=True)
    special_notes = models.CharField(max_length=500, null=True, blank=True)
    certifications_required = models.CharField(max_length=500, null=True, blank=True)
    packaging_requirements = models.CharField(max_length=500, null=True, blank=True)
    additional_notes = models.CharField(max_length=500, null=True, blank=True)
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_assigned",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                original = Inquiry.objects.get(pk=self.pk)
                if original.assigned_user is None and self.assigned_user is not None:
                    self.status = "Assigned"
            except Inquiry.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def upload_doc(self, doc_dict: dict = {}, max_size_override: dict = None):
        error_list = []
        logger.info("Document upload initiated with the following files: %s", doc_dict)

        allowed_types = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
        ]
        default_max_size = 2 * 1024 * 1024
        max_size_override = max_size_override or {}

        for attr, doc in doc_dict.items():
            if doc is not None:
                logger.info(f"Processing file for {attr}: {doc.name}")
                file_extension = os.path.splitext(doc.name)[1].lower()

                if file_extension not in allowed_types:
                    raise ValidationError(
                        {
                            attr: f"Invalid file type {file_extension} for {attr}. Allowed: {', '.join(allowed_types)}"
                        }
                    )

                max_size = max_size_override.get(attr, default_max_size)

                if doc.size > max_size:
                    size_mb = max_size / (1024 * 1024)
                    raise ValidationError(
                        {
                            attr: f"File size too large for {attr}. Maximum allowed size is {size_mb:.1f} MB."
                        }
                    )

                current_value = getattr(self, attr, None)
                try:
                    if current_value:
                        delete_uploaded_file(current_value)

                    upload_folder = f"{attr}/"
                    new_value, _ = upload_doc_file(
                        doc, allowed_types, upload_folder, self.id, None
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

    class Meta:
        db_table = "Inquiry"
        permissions = [
            ("print_inquiry_pdf_copy", "Can print inquiry"),
            ("download_inquiry_excel_copy", "Can download inquiry Excel"),
            ("download_inquiry_pdf_copy", "Can download inquiry PDF"),
        ]

    def __str__(self):
        return self.inquiry_number or f"Inquiry {self.id}"


class InquiryDetail(models.Model):
    STANDARD_CONFIRMATION_CHOICE = (
        ("EN", "EN"),
        ("IS", "IS"),
        ("ASTM", "ASTM"),
        ("JIS", "JIS"),
        ("Others", "Others"),
    )
    POST_OPERATION_CHOICE = (
        ("Drilling", "Drilling"),
        ("Punching", "Punching"),
        ("Machining", "Machining"),
        ("Tapping", "Tapping"),
        ("Banding", "Banding"),
        ("Others", "Others"),
    )
    inquiry = models.ForeignKey(
        Inquiry, on_delete=models.CASCADE, related_name="inquiry_details", null=True
    )
    section_no = models.CharField(max_length=20, db_index=True, null=True, blank=True)
    description = models.CharField(max_length=250, null=True, blank=True)
    standard_confirmation = models.CharField(
        max_length=20, null=True, blank=True, choices=STANDARD_CONFIRMATION_CHOICE
    )
    standard_confirmation_other = models.CharField(
        max_length=250, null=True, blank=True
    )
    standard_confirmation = models.CharField(
        max_length=20, default="EN", choices=STANDARD_CONFIRMATION_CHOICE
    )
    standard_confirmation_other = models.CharField(
        max_length=250, null=True, blank=True
    )
    alloy = models.ForeignKey(
        Alloy, on_delete=models.CASCADE, related_name="inquiry_detail_alloy", null=True
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        related_name="inquiry_detail_temper",
        null=True,
    )
    length = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    tolerance = models.CharField(max_length=20, null=True, blank=True)
    tolerance_plus = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    tolerance_minus = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    surface_finish = models.ManyToManyField(
        JobWorkType,
        related_name="inquiry_detail_jobwork",
        blank=True,
    )
    out_source = models.BooleanField(default=False, null=True)
    cutting = models.BooleanField(default=False, null=True)
    machining = models.BooleanField(default=False, null=True)
    deburring = models.BooleanField(default=False, null=True)
    cutting_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    machining_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    deburring_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    anodising = models.BooleanField(default=False, null=True)
    powder_coating = models.BooleanField(default=False, null=True)
    pvdf = models.BooleanField(default=False, null=True)
    anodising_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    anodising_description = models.CharField(max_length=250, null=True)
    powder_coating_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    powder_coating_description = models.CharField(max_length=250, null=True)
    pvdf_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    pvdf_description = models.CharField(max_length=250, null=True)
    laser_marking_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    laser_marking_description = models.CharField(max_length=250, null=True)
    post_operation = models.CharField(
        max_length=100, null=True, blank=True, choices=POST_OPERATION_CHOICE
    )
    post_operation_other = models.CharField(max_length=250, null=True, blank=True)
    end_application = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_detail_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_detail_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_detail_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    def upload_drawings(self, files: list):
        allowed_types = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx"]
        max_file_size = 2 * 1024 * 1024
        for doc in files:
            if doc is None:
                continue
            file_extension = os.path.splitext(doc.name)[1].lower()
            if file_extension not in allowed_types:
                raise ValidationError({"drawing_attachment": f"Invalid file type {file_extension}. Allowed: {', '.join(allowed_types)}"})
            if doc.size > max_file_size:
                raise ValidationError({"drawing_attachment": "File size too large. Maximum allowed size is 2 MB."})
            upload_folder = "drawing_attachment/"
            new_value, _ = upload_doc_file(doc, allowed_types, upload_folder, self.id, None)
            if new_value:
                InquiryDetailDrawing.objects.create(inquiry_detail=self, file_path=new_value)
            else:
                raise ValidationError({"drawing_attachment": f"Failed to upload {doc.name}"})

    def upload_doc(self, doc_dict: dict = {}):
        error_list = []
        logger.info("Document upload initiated with the following files: %s", doc_dict)

        allowed_types = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
        ]
        max_file_size = 2 * 1024 * 1024
        allowed_types = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
        ]
        max_file_size = 2 * 1024 * 1024

        for attr, doc in doc_dict.items():
            if doc is not None:
                logger.info(f"Processing file for {attr}: {doc.name}")
                file_extension = os.path.splitext(doc.name)[1].lower()

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

                    upload_folder = f"{attr}/"
                    new_value, _ = upload_doc_file(
                        doc, allowed_types, upload_folder, self.id, None
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

    class Meta:
        db_table = "Inquiry_Detail"
        permissions = [
            ("download_inquiry_detail_excel_copy", "Can download inquiry detail Excel"),
            ("download_inquiry_detail_pdf_copy", "Can download inquiry detail PDF"),
        ]

    def __str__(self):
        return self.section_no or f"Detail {self.id}"


class InquiryDetailDrawing(models.Model):
    inquiry_detail = models.ForeignKey(
        InquiryDetail, on_delete=models.CASCADE, related_name="drawings"
    )
    file_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Inquiry_Detail_Drawing"

    def __str__(self):
        return f"Drawing for {self.inquiry_detail_id}"
