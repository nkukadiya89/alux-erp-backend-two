from decimal import Decimal
import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from bloster.models import BlosterMaster
from customer.models import Customer
from product.models import Alloy, Temper
from settings.models import BaseModule
from utils.aws_file_upload import delete_uploaded_file, upload_doc_file
from multiselectfield import MultiSelectField
logger = logging.getLogger("file")


class DiePress(BaseModule):
    code = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=100, db_index=True, null=True, blank=True)
    capacity = models.FloatField(null=True, blank=True)
    billet_diameter = models.FloatField(null=True, blank=True)
    billet_length_min = models.FloatField(null=True, blank=True)
    billet_length_max = models.FloatField(null=True, blank=True)
    billet_weight = models.FloatField(null=True, blank=True)
    billet_wt_factor = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    container_diameter = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    container_area = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    extrusion_length_min = models.FloatField(null=True, blank=True)
    extrusion_length_max = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
            models.Index(fields=["name", "deleted"]),
        ]
        permissions = [
            ("download_profile_press_pdf_copy", "Can download profile press PDF"),
            ("download_profile_press_excel_copy", "Can download profile press Excel"),
        ]


class DieGroup(BaseModule):
    name = models.CharField(max_length=50,unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
        ]
        permissions = [
            ("download_profile_group_pdf_copy", "Can download profile group PDF"),
            ("download_profile_group_excel_copy", "Can download profile group Excel"),
        ]
        

class DieCategory(BaseModule):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
        ]
        permissions = [
            ("download_profile_category_pdf_copy", "Can download profile category PDF"),
            (
                "download_profile_category_excel_copy",
                "Can download profile category Excel",
            ),
        ]


class DieSubCategory(BaseModule):
    name = models.CharField(max_length=50,unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
        ]
        permissions = [
            (
                "download_profile_sub_category_pdf_copy",
                "Can download profile sub category PDF",
            ),
            (
                "download_profile_sub_category_excel_copy",
                "Can download profile sub category Excel",
            ),
        ]


class DieType(BaseModule):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}"


class DieSize(BaseModule):
    diameter = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    thickness = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    def __str__(self):
        return f"{self.diameter} - {self.thickness}"

    class Meta:
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
        ]
        permissions = [
            ("download_profile_size_pdf_copy", "Can download profile size PDF"),
            ("download_profile_size_excel_copy", "Can download profile size Excel"),
        ]


class Die(BaseModule):

    DIE_TYPE = [
        ("Solid", "Solid"),
        ("Hollow", "Hollow"),
        ("Semi Hollow", "Semi Hollow"),
    ]

    SOLID_OPTIONS = [
        ("Full Set", "Full Set"),
        ("Die Plate", "Die Plate"),
        ("Feeder", "Feeder"),
    ]

    HOLLOW_OPTIONS = [
        ("Die Plate", "Die Plate"),
        ("Mandrel", "Mandrel"),
    ]

    OWNERSHIP_TYPE = [("exclusive", "exclusive"), ("non_exclusive", "non_exclusive")]

    SEMI_HOLLOW_OPTIONS = [
        ("Die Plate", "Die Plate"),
        ("Mandrel", "Mandrel"),
    ]

    DIE_DETAILS = {
        "Solid": {
            "Die Plate": [("Backer Number", "Backer Number")],
            "Feeder": [("Feeder Number", "Feeder Number")],
        },
        "Hollow": {
            "Die Plate": [("Backer Number", "Backer Number")],
            "Mandrel": [("Diameter", "Diameter"), ("Thickness", "Thickness")],
        },
        "Semi Hollow": {
            "Die Plate": [("Backer Number", "Backer Number")],
            "Mandrel": [("Diameter", "Diameter"), ("Thickness", "Thickness")],
        },
    }
    description = models.TextField(null=True, blank=True)
    cutting_dimensions = models.JSONField(default=list, null=True, blank=True)
    die_number = models.CharField(max_length=255, db_index=True)
    dimension1 = models.DecimalField(
        decimal_places=2, max_digits=10, db_index=True, null=True, blank=True
    )
    dimension2 = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    dimension3 = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    dimension4 = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    min_wt_kg_p_mt = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    max_wt_kg_p_mt = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    ownership_type = models.CharField(
        max_length=20, choices=OWNERSHIP_TYPE, default="non_exclusive"
    )
    customer = models.ForeignKey(
        "customer.Customer",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dies",
        db_index=True,
    )

    die_group = models.ForeignKey(
        "DieGroup",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dies",
        db_index=True,
    )
    die_category = models.ForeignKey(
        "DieCategory",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dies",
        db_index=True,
    )
    die_sub_category = models.ForeignKey(
        "DieSubCategory",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dies",
        db_index=True,
    )

    die_diagram = models.CharField(max_length=250, null=True, blank=True)
    die_detail_diagram = models.CharField(max_length=250, null=True, blank=True)
    customer_approved_diagram = models.CharField(max_length=250, null=True, blank=True)
    autocad_drawing = models.CharField(max_length=250, null=True, blank=True)
    die_manufacturing = models.CharField(max_length=255, null=True, blank=True)
    die_sop = models.CharField(max_length=250, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    customer_reference_number = models.CharField(max_length=250, null=True, blank=True)

    die_type = models.CharField(max_length=20, choices=DIE_TYPE, default="Solid")

    ccd_mm = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    perimeter_outer = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    area = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )

    process_description = models.TextField(null=True, blank=True)

    wt_kg_p_mt = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    front_end_process_loss_mm = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    back_end_process_loss_mm = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    stretching_head_loss_mm = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    stretching_tail_loss_mm = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    total_process_loss_mm = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    total_process_loss_meter = models.DecimalField(
        decimal_places=4, max_digits=10, null=True, blank=True
    )
    total_process_loss_kg = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        zero = Decimal("0")
        self.total_process_loss_mm = (
            (self.front_end_process_loss_mm or zero)
            + (self.back_end_process_loss_mm or zero)
            + (self.stretching_head_loss_mm or zero)
            + (self.stretching_tail_loss_mm or zero)
        )
        self.total_process_loss_meter = self.total_process_loss_mm / Decimal("1000")
        if self.wt_kg_p_mt:
            self.total_process_loss_kg = self.total_process_loss_meter * self.wt_kg_p_mt
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Die {self.die_number} - {self.die_type}"

    class Meta:
        db_table = "die"
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
            models.Index(fields=["die_number", "deleted"]),
            models.Index(fields=["die_type", "deleted"]),
        ]
        permissions = [
            ("print_profile_pdf_copy", "Can print profile"),
            (
                "print_profile_workorder_report_pdf_copy",
                "Can print profile workorder report",
            ),
            ("download_profile_pdf_copy", "Can download profile PDF"),
            ("download_profile_excel_copy", "Can download profile Excel"),
        ]

    def get_options(self):
        options_map = {
            "Solid": self.SOLID_OPTIONS,
            "Hollow": self.HOLLOW_OPTIONS,
            "Semi Hollow": self.SEMI_HOLLOW_OPTIONS,
        }
        return options_map.get(self.die_type, [])

    def get_details(self):
        return self.DIE_DETAILS.get(self.die_type, {}).get(self.die_option, [])

    def clean(self):
        """
        Custom validation for Die model.
        """
        if self.die_type == "Solid":
            if self.die_option == "Die Plate" and not self.backer_number:
                raise ValidationError(
                    {
                        "detail_key": "Backer Number is required for Solid Die with Die Plate option."
                    }
                )
            if self.die_option == "Feeder":
                if not all([self.feeder_number]):
                    raise ValidationError(
                        {
                            "feeder_number": "Feeder Number is required for Solid Die with Feeder option.",
                        }
                    )

        if self.die_type == "Hollow" and not self.die_option:
            raise ValidationError({"option": "Option is required for Hollow Die type."})

        if self.die_type == "Semi Hollow" and not self.die_option:
            raise ValidationError(
                {"option": "Option is required for Semi Hollow Die type."}
            )

    def upload_doc(self, doc_dict: dict = {}):
        """
        Uploads documents to the file storage for the given die instance.
        Docs can be of type .pdf and will be uploaded under the die folder
        with the die ID. If a file already exists, it will be replaced.

        :param doc_dict: Dictionary of documents to upload (key: field name, value: file object)
        :return: None or raises a ValidationError
        """
        error_list = []
        logger.info("Document upload initiated with the following files: %s", doc_dict)

        allowed_types_mapping = {
            "die_diagram": [".pdf", ".jpg", ".jpeg", ".png"],
            "customer_approved_diagram": [".pdf", ".jpg", ".jpeg", ".png"],
            "autocad_drawing": [".dwg"],
            "die_manufacturing": [".dwg"],
            "die_detail_diagram": [".pdf"],
            "die_sop": [".pdf"],
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
                        doc, allowed_types, "Die/", self.id, None
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

    def get_item_name(self):
        if self.dimension1 is None:
            return "N/A"
        dims = [f"{self.dimension1:.2f}"]
        for d in [self.dimension2, self.dimension3, self.dimension4]:
            if d is not None:
                dims.append(f"{d:.2f}")
        return f"{' x '.join(dims)}"


class DieInformation(models.Model):
    section = models.ForeignKey(
        "Die",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="extrusion_die_info",
        db_index=True,
    )
    reference_drawing_number = models.CharField(max_length=250, null=True, blank=True)
    revision = models.CharField(max_length=250, null=True, blank=True)
    revision_date = models.DateField(null=True, blank=True)
    container_size = models.IntegerField(null=True, blank=True)
    revision_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "die_information"

    def __str__(self):
        return f"Die Info - Die{self.reference_drawing_number}"


class SectionBallonDimensions(BaseModule):
    section = models.ForeignKey(
        "Die",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ballon_drawing_dimensions",
        db_index=True,
    )
    balloon_no = models.IntegerField(null=True, blank=True)
    dim_type = models.CharField(max_length=60, null=True, blank=True)
    nominal_value = models.CharField(max_length=30, null=True, blank=True)
    tolerance_plus = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tolerance_minus = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    min_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    max_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    description = models.TextField(null=True, blank=True)
    is_inspection = models.BooleanField(default=True)
    is_critical = models.BooleanField(default=False)
    pos_x = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pos_y = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    instrument_used_for_inspection = models.CharField(
        max_length=50, null=True, blank=True
    )

    class Meta:
        db_table = "section_ballon_dimensions"
        indexes = [
            models.Index(fields=["section", "deleted"]),
        ]

    def __str__(self):
        return f"Ballon {self.balloon_no} - Die{self.section_id} "


class DieTool(models.Model):
    RUN_UNDER_DEVIATION = (
        ("active", "active"),
        ("inactive", "inactive"),
        ("under development", "under development"),
        ("scrapped", "scrapped"),
        ("repair", "repair"),
    )
    DIE_TOOL_STATUS = (
        ("Available", "Available"),
        ("Reserved", "Reserved"),
        ("In_Production", "In_Production"),
        ("Under_Maintenance", "Under_Maintenance"),
        ("Under_Correction", "Under_Correction"),
        ("Under_Inspection", "Under_Inspection"),
        ("Scrapped", "Scrapped"),
    )
    RUN_UNDER_DEVIATION_INACTIVE = (
        ("die_broken", "die_broken"),
        ("die_absolute", "die_absolute"),
        ("die_shift", "die_shift"),
        ("other", "other"),
    )
    BROKEN_PART_CHOICES = (
        ('die_plate', 'Die Plate'),
        ('mandrel', 'Mandrel'),
        ('backer', 'Backer'),
        ('bolster', 'Bolster'),
        ('feeder', 'Feeder'),
        ('die_ring', 'Die Ring'),
        ('pocket', 'Pocket')
    )
    DAMAGE_SEVERITY_CHOICES = (
        ("minor", "Minor"),
        ("major", "Major"),
        ("critical", "Critical"),
    )
    DIE_TOOL_LOCATION = (
        ("Die_Tool_Room", "Die_Tool_Room"),
        ("Press", "Press"),
        ("Maintenance", "Maintenance"),
        ("QC_Inspection", "QC_Inspection"),
        ("Vendor", "Vendor"),
        ("Scrap", "Scrap"),
    )
    OWNERSHIP = (("own", "own"), ("customer", "customer"))
    TRIAL_RESULT = (("ok", "ok"), ("correction", "correction"), ("failed", "failed"))

    die = models.ForeignKey(Die, on_delete=models.CASCADE, related_name="dietool_die")
    actual_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    drawing_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    weight_diff_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    weight_diff_per = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tool_number = models.CharField(max_length=25)
    die_size = models.ForeignKey(
        DieSize, on_delete=models.CASCADE, null=True, related_name="dietool_diesize"
    )
    die_cavity = models.IntegerField(default=0, validators=[MaxValueValidator(10)])
    vendor = models.ForeignKey(
        Customer, on_delete=models.CASCADE, null=True, related_name="dietool_vendor"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, null=True, related_name="dietool_customer"
    )
    developer_ref_no = models.CharField(max_length=150, null=True, blank=True)
    eligible_for_press = models.ForeignKey(
        DiePress,
        on_delete=models.CASCADE,
        related_name="die_tool_eligible_for_press",
        null=True,
    )
    first_bloster = models.ManyToManyField(
        BlosterMaster,
        related_name="dietool_bloster_first",
        blank=True,
    )
    second_bloster = models.ManyToManyField(
        BlosterMaster,
        related_name="dietool_bloster_second",
        blank=True,
    )
    third_bloster = models.ManyToManyField(
        BlosterMaster,
        related_name="dietool_bloster_third",
        blank=True,
    )
    received_date = models.DateField(null=True)
    order_date = models.DateField(null=True)

    total_running_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    max_die_life = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    remaining_life = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tool_status = models.CharField(
        choices=RUN_UNDER_DEVIATION,
        max_length=25,
        null=True,
        default="under development",
    )
    tool_status_inactive = models.CharField(
        choices=RUN_UNDER_DEVIATION_INACTIVE, max_length=25, null=True
    )
    broken_part = MultiSelectField(choices=BROKEN_PART_CHOICES, null=True, blank=True)
    damage_severity = models.CharField(max_length=50, choices=DAMAGE_SEVERITY_CHOICES, null=True, blank=True)
    location = models.CharField(max_length=50, choices=DIE_TOOL_LOCATION, default="Die_Tool_Room")
    status = models.CharField(max_length=20, choices=DIE_TOOL_STATUS, default="Available")
    die_broken_note = models.TextField(null=True, blank=True)
    material_grade = models.CharField(max_length=150, null=True, blank=True)
    tool_status_reason = models.CharField(max_length=255, null=True)
    ownership = models.CharField(choices=OWNERSHIP, max_length=150, null=True)
    is_active = models.BooleanField(default=True)
    remarks = models.CharField(max_length=170, null=True, blank=True)
    drawing_no = models.CharField(max_length=150, null=True)
    die_oblique_number = models.CharField(max_length=150, null=True, blank=True)

    # Storage Location
    rac_no = models.CharField(max_length=50, null=True)
    row_no = models.CharField(max_length=50, null=True)
    column_no = models.CharField(max_length=50, null=True)
    die_location = models.CharField(max_length=50, null=True)

    die_option = models.CharField(max_length=20, blank=True, null=True)
    diameter = models.FloatField(
        blank=True,
        null=True,
        help_text="Diameter value for Insert option.",
    )
    thickness = models.FloatField(
        blank=True,
        null=True,
        help_text="Thickness value for Insert option.",
    )
    backer_number = models.CharField(max_length=250, blank=True, null=True)
    extrusion_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    feeder_number = models.CharField(max_length=250, blank=True, null=True)

    scrap_date = models.DateField(null=True, blank=True)
    scrap_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    scrap_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dietool_scrap_approved_by",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dietool_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dietool_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dietool_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.die} - {self.tool_number}"

    class Meta:
        db_table = "die_tool"
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
            models.Index(fields=["die", "deleted"]),
            models.Index(fields=["tool_number", "deleted"]),
        ]
        permissions = [
            ("download_profile_tool_pdf_copy", "Can download profile tool PDF"),
            ("download_profile_tool_excel_copy", "Can download profile tool Excel"),
        ]

class DieToolBrokenImage(models.Model):
    die_tool = models.ForeignKey(DieTool, on_delete=models.CASCADE, null=True, related_name="die_broken_images")
    image = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.die_tool.tool_number} Image"

    class Meta:
        db_table = "die_tool_broken_image"

    @classmethod
    def upload_doc(cls, die_tool_instance, images: list):
        MAX_FILE_SIZE = 2 * 1024 * 1024
        ALLOWED_TYPES = [".jpg", ".jpeg", ".png"]

        existing_count = die_tool_instance.die_broken_images.count()
        if existing_count + len(images) > 4:
            raise ValidationError({"die_broken_images": "Maximum 4 images allowed."})

        for image in images:
            if image.size > MAX_FILE_SIZE:
                raise ValidationError({"die_broken_images": "Maximum file size allowed is 2 MB."})

            file_extension = os.path.splitext(image.name)[1].lower()
            if file_extension not in ALLOWED_TYPES:
                raise ValidationError({"die_broken_images": f"Invalid file type {file_extension}."})

            new_image_path, _ = upload_doc_file(
                image, ALLOWED_TYPES, "DieToolBrokenImage/", die_tool_instance.id, None
            )
            cls.objects.create(die_tool=die_tool_instance, image=new_image_path)



class ConversionRate(BaseModule):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="conversionrate_customer",
        null=True,
    )

    def __str__(self):
        return f"{self.customer}"

    class Meta:
        db_table = "conversion_rate"
        permissions = [
            ("download_conversion_rate_pdf_copy", "Can download conversion rate PDF"),
            (
                "download_conversion_rate_excel_copy",
                "Can download conversion rate Excel",
            ),
        ]


class ConversionRateItems(BaseModule):
    conversion_rate = models.ForeignKey(
        ConversionRate,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
    )
    die = models.ForeignKey(
        Die, on_delete=models.CASCADE, related_name="conversionrateitems_die", null=True
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        related_name="conversionrateitems_alloy",
        null=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        related_name="conversionrateitems_temper",
        null=True,
    )

    def __str__(self):
        return f"{self.conversion_rate} - {self.alloy} - {self.temper}"

    class Meta:
        db_table = "conversion_rate_items"
        permissions = [
            (
                "download_conversion_rate_items_pdf_copy",
                "Can download conversion rate items PDF",
            ),
            (
                "download_conversion_rate_items_excel_copy",
                "Can download conversion rate items Excel",
            ),
        ]


class ConversionRateVersions(BaseModule):
    ADJUSTMENT_TYPE_CHOICES = (
        ("Increase", "Increase"),
        ("Decrease", "Decrease"),
        ("Initial", "Initial"),
    )
    conversion_rate_items = models.ForeignKey(
        ConversionRateItems,
        on_delete=models.CASCADE,
        related_name="versions",
        null=True,
    )
    date = models.DateField(auto_now_add=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    conversion = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    old_conversion = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    new_conversion = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    difference = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    percentage_change = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    adjustment_type = models.CharField(
        max_length=20, choices=ADJUSTMENT_TYPE_CHOICES, default="Initial"
    )
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.conversion_rate_items} - {self.conversion} - {self.adjustment_type}"
        )

    class Meta:
        db_table = "conversion_rate_versions"
        permissions = [
            (
                "download_conversion_rate_versions_pdf_copy",
                "Can download conversion rate versions PDF",
            ),
            (
                "download_conversion_rate_versions_excel_copy",
                "Can download conversion rate versions Excel",
            ),
        ]
