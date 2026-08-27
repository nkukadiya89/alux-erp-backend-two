import os
from venv import logger

from django.conf import settings
from django.db import models
from django.forms import ValidationError
from product.models import Item
from user.models import User
from material.models import Material
from transporter.models import Transporter
from utils.aws_file_upload import delete_uploaded_file, upload_doc_file
from vehicle_master.models import VehicleMaster
from vehicle_type.models import VehicleType


class ManualWeightEntry(models.Model):
    cash_party_name = models.CharField(max_length=200, null=True, blank=True)
    gross_weight = models.DecimalField(
        max_digits=50, decimal_places=3, null=True, blank=True
    )
    tare_weight = models.DecimalField(
        max_digits=50, decimal_places=3, null=True, blank=True
    )
    net_weight = models.DecimalField(
        max_digits=50, decimal_places=3, null=True, blank=True
    )
    date_time_first = models.DateTimeField()
    date_time_second = models.DateTimeField()
    mound = models.DecimalField(max_digits=50, decimal_places=3, null=True, blank=True)
    capture_photo_manual_1 = models.CharField(max_length=500, null=True, blank=True)
    capture_photo_manual_2 = models.CharField(max_length=500, null=True, blank=True)
    serial_no = models.CharField(max_length=100, null=True, blank=True)
    total_copy = models.IntegerField(default=1)
    vehicle_no = models.ForeignKey(
        VehicleMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_weight_entry_vehicle_no",
    )
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.CASCADE,
        null=True,
        related_name="manual_weight_entry_vehicletype",
    )
    party_name = models.ForeignKey(
        Transporter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"deleted": False, "is_active": "active"},
    )
    purchaser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_weight_purchaser_weight_entries",
        limit_choices_to={"groups__name": "Purchaser", "is_active": True},
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_weigt_seller_weight_entries",
    )

    party_mobile_no = models.CharField(max_length=20, null=True, blank=True)
    material = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="manual_weight_entry_material",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_weight_entry_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_weight_entry_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_weight_entry_deleted",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

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
        default_max_size = 10 * 1024 * 1024  # Increased from 2MB to 10MB

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
        db_table = "manual_weight_entry"
        permissions = [
            (
                "download_manual_weight_entry_excel_copy",
                "Can download manual weight entry Excel",
            ),
            (
                "download_manual_weight_entry_pdf_copy",
                "Can download manual weight entry PDF",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.gross_weight is not None and self.tare_weight is not None:
            try:
                self.net_weight = self.gross_weight - self.tare_weight
            except Exception:
                self.net_weight = None
        if self.net_weight is not None:
            try:
                self.mound = self.net_weight / 20
            except Exception:
                self.mound = None
        super().save(*args, **kwargs)
