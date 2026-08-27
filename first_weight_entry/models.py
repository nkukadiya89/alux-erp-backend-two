import os
from venv import logger

from django.conf import settings
from django.db import models
from django.forms import ValidationError
from user.models import User
from material.models import Material
from transporter.models import Transporter
from utils.aws_file_upload import delete_uploaded_file, upload_doc_file
from vehicle_master.models import VehicleMaster
from vehicle_type.models import VehicleType
from product.models import Item

# Create your models here.


class FirstWeightEntry(models.Model):

    WEIGHT_FOR = [
        ("gross weight", "Gross weight"),
        ("tare weight", "Tare weight"),
    ]

    WEIGHT_AUTOMATIC = [
        ("yes", "Yes"),
        ("no", "No"),
    ]

    weight_for = models.CharField(
        max_length=50, choices=WEIGHT_FOR, default="gross weight"
    )
    cash_party_name = models.CharField(max_length=200, null=True, blank=True)
    weight_automatic = models.CharField(
        max_length=50, choices=WEIGHT_AUTOMATIC, default="no"
    )
    gross_weight = models.DecimalField(
        max_digits=50, decimal_places=3, null=True, blank=True
    )
    tare_weight = models.DecimalField(
        max_digits=50, decimal_places=3, null=True, blank=True
    )
    net_weight = models.DecimalField(
        max_digits=50, decimal_places=3, null=True, blank=True
    )
    date_time_first = models.DateTimeField(auto_now_add=True)
    date_time_second = models.DateTimeField(null=True, blank=True)
    mound = models.DecimalField(max_digits=50, decimal_places=3, null=True, blank=True)
    capture_photo = models.CharField(max_length=500, null=True, blank=True)
    capture_photo_2 = models.CharField(max_length=500, null=True, blank=True)
    serial_no = models.IntegerField(null=True, blank=True)
    total_copy = models.IntegerField(default=1)
    is_second_entry_done = models.BooleanField(default=False)
    vehicle_no = models.ForeignKey(
        VehicleMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="first_weight_entry_vehicle_no",
    )
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.CASCADE,
        null=True,
        related_name="first_weight_entry_vehicletype",
    )
    party_name = models.ForeignKey(
        Transporter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    purchaser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchaser_weight_entries",
        limit_choices_to={"groups__name": "Purchaser", "is_active": True},
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seller_weight_entries",
    )
    party_mobile_no = models.CharField(max_length=20, null=True, blank=True)
    material = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="first_weight_entry_material",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="first_weight_entry_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="first_weight_entry_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="first_weight_entry_deleted",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.vehicle_no} - {self.party_name}"

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
        default_max_size = 10 * 1024 * 1024

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
        db_table = "first_weight_entry"
        permissions = [
            (
                "download_first_weight_entry_excel_copy",
                "Can download first weight entry Excel",
            ),
            (
                "download_first_weight_entry_pdf_copy",
                "Can download first weight entry PDF",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.serial_no:
            last_entry = FirstWeightEntry.objects.order_by("-serial_no").first()
            if last_entry and last_entry.serial_no:
                self.serial_no = last_entry.serial_no + 1
            else:
                self.serial_no = 1

        if self.weight_for == "tare weight" and self.vehicle_no:
            if self.vehicle_no.tare_wt:
                self.tare_weight = self.vehicle_no.tare_wt
        super().save(*args, **kwargs)
