import logging
import os
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

from common.models import JobWorkType, PackingMode
from customer.models import Customer
from die.models import Die
from inquiry_salesorder.models import InquirySalesOrder, InquirySalesOrderDetail
from product.models import Alloy, Temper
from settings.models import BaseModule
from utils.aws_file_upload import delete_uploaded_file, upload_doc_file
from workorder.process_constants import PROCESS_STAGE_CHOICES

logger = logging.getLogger("file")


class WorkOrder(BaseModule):
    NALCO_TYPE_CHOICE = (
        ("Fixed", "Fixed"),
        ("Variable", "Variable"),
    )

    ORDER_TYPE_CHOICES = (
        ("order", "Order"),
        ("trial", "Trial"),
    )

    STATUS_CHOICE = (
        ("W/o create", "W/o create"),
        ("App- MKT Dpt", "App- MKT Dpt"),
        ("App- Design Dpt", "App- Design Dpt"),
        ("App-Management", "App-Management"),
        ("Open", "Open"),
        ("Planning", "Planning"),
        (
            "Under Production- Extru / Insp / Ageing/QC",
            "Under Production- Extru / Insp / Ageing/QC",
        ),
        ("Wating for packing", "Wating for packing"),
        ("Packed", "Packed"),
        ("Dispatched", "Dispatched"),
        ("Closed", "Closed"),
    )

    TOLERANCE_CHOICE = (
        ("Zero(0)", "Zero(0)"),
        ("+-3%", "+-3%"),
        ("+-5%", "+-5%"),
        ("+-7%", "+-7%"),
        ("+-10%", "+-10%"),
        ("+3%", "+3%"),
        ("+5%", "+5%"),
        ("+7%", "+7%"),
        ("+10%", "+10%"),
        ("-3%", "-3%"),
        ("-5%", "-5%"),
        ("-7%", "-7%"),
        ("-10%", "-10%"),
    )

    WORKORDER_TYPES = (
        ("In_House", "In_House"),
        ("Job_Work", "Job_Work"),
    )

    bill_to = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="workorder_customer_bill_to",
        null=True,
        db_index=True,
    )
    ship_to = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="workorder_customer_ship_to",
        null=True,
        db_index=True,
    )
    salesorder = models.OneToOneField(
        InquirySalesOrder,
        on_delete=models.SET_NULL,
        related_name="workorder_inquiry_salesorder",
        null=True,
        db_index=True,
    )
    reference_wo = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_workorders",
    )
    order_date = models.DateField(null=True)
    delivery_date = models.DateField(null=True)
    purchase_order_no = models.CharField(max_length=25, blank=True)
    purchase_order_date = models.DateField(null=True)
    order_type = models.CharField(
        choices=ORDER_TYPE_CHOICES, default="order", max_length=50
    )
    project_name = models.CharField(max_length=250, null=True)
    nalco_type = models.CharField(
        choices=NALCO_TYPE_CHOICE, default="Variable", max_length=100, null=True
    )
    tolerance = models.CharField(
        choices=TOLERANCE_CHOICE, default="Zero(0)", max_length=100, null=True
    )
    remarks = models.TextField(null=True)
    packing_mode = models.ManyToManyField(
        PackingMode,
        related_name="workorder_packing_modes",
        blank=True,
    )
    status = models.CharField(
        choices=STATUS_CHOICE, default="W/o create", max_length=250, null=True
    )
    # Parallel process-tracking status (does not replace legacy `status`)
    process_status = models.CharField(
        choices=PROCESS_STAGE_CHOICES,
        default="WO_CREATED",
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
    )
    order_no = models.CharField(max_length=100, null=True, db_index=True)
    planning_status = models.BooleanField(default=False)
    packing_mode_other_reason = models.CharField(max_length=250, null=True)
    po_copy = models.CharField(max_length=250, null=True)
    reason_to_close = models.TextField(null=True, blank=True)
    wo_closing_doc = models.CharField(max_length=250, null=True)

    workorder_type = models.CharField(
        choices=WORKORDER_TYPES, default="In_House", max_length=250, null=True
    )
    terms_and_condition = models.TextField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workorder_approved",
    )

    def save(self, *args, **kwargs):
        """Set delivery_date automatically to 12 days after order_date."""
        if not self.delivery_date:
            self.delivery_date = now().date() + timedelta(days=12)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bill_to} - {self.order_date}"

    def upload_doc(self, doc_dict: dict = {}):
        error_list = []
        logger.info("Document upload initiated with the following files: %s", doc_dict)

        allowed_types_mapping = {
            "po_copy": [
                ".pdf",
                ".jpg",
                ".jpeg",
                ".png",
                ".doc",
                ".docx",
                ".xls",
                ".xlsx",
            ],
            "wo_closing_doc": [
                ".pdf",
                ".jpg",
                ".jpeg",
                ".png",
                ".doc",
                ".docx",
                ".xls",
                ".xlsx",
            ],
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
        db_table = "workorder"
        indexes = [
            models.Index(fields=["deleted", "status"], name="wo_deleted_status_idx"),
            models.Index(fields=["deleted", "-order_date"], name="wo_deleted_date_idx"),
            models.Index(
                fields=["deleted", "bill_to", "status"], name="wo_customer_status_idx"
            ),
            models.Index(fields=["status", "deleted"], name="wo_status_deleted_idx"),
        ]
        permissions = [
            ("print_workorder_copy", "Can print workorder copy"),
            ("print_production_copy", "Can print production copy"),
            ("print_packing_copy", "Can print packing copy"),
            ("print_account_sales_copy", "Can print account sales copy"),
            ("print_workorder_report", "Can print workorder report"),
            (
                "download_workorder_report_excel_copy",
                "Can download workorder report Excel",
            ),
            (
                "download_workorder_excel_copy",
                "Can download workorder Excel",
            ),
            ("change_profile_over_weight", "Can change profile over weight"),
        ]


class WorkOrderDetail(BaseModule):
    STATUS_CHOICE = (
        ("Packed", "Packed"),
        ("Pending", "Pending"),
        ("In-Process", "In-Process"),
        ("Dispatched", "Dispatched"),
        ("In-Planning", "In-Planning"),
        ("In-Production", "In-Production"),
        ("In-Priority", "In-Priority"),
    )

    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="workorder_detail_workorder",
        null=True,
        db_index=True,
    )
    salesorder_detail = models.ForeignKey(
        InquirySalesOrderDetail,
        on_delete=models.CASCADE,
        related_name="workorder_detail_salesorder",
        null=True,
        db_index=True,
    )
    die_profile = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        related_name="workorder_detail_die",
        null=True,
        db_index=True,
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        related_name="workorder_detail_alloy",
        null=True,
        db_index=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        related_name="workorder_detail_temper",
        null=True,
        db_index=True,
    )

    surface_finish = models.ManyToManyField(
        JobWorkType, related_name="workorder_details", blank=True
    )

    out_source = models.BooleanField(default=False, null=True)

    laser_marking_description = models.CharField(max_length=250, null=True)
    laser_marking_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True
    )

    cutting = models.BooleanField(default=False, null=True)
    machining = models.BooleanField(default=False, null=True)
    deburring = models.BooleanField(default=False, null=True)

    cutting_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    machining_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    deburring_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)

    anodising = models.BooleanField(default=False, null=True)
    powder_coating = models.BooleanField(default=False, null=True)
    pvdf = models.BooleanField(default=False, null=True)

    anodising_description = models.CharField(max_length=250, null=True)
    anodising_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)

    powder_coating_description = models.CharField(max_length=250, null=True)
    powder_coating_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True
    )

    pvdf_description = models.CharField(max_length=250, null=True)
    pvdf_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)

    length = models.IntegerField(default=0, null=True)
    pieces = models.IntegerField(default=0, null=True)
    net_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    max_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    min_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    nalco_rate = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    packing_cost = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    customer_reference_number = models.CharField(max_length=250, null=True, blank=True)
    conversion = models.DecimalField(decimal_places=2, max_digits=10, null=True)

    description = models.CharField(max_length=250, null=True)
    modify_nalco_rate = models.BooleanField(default=False)
    nalco_rate_change_reason = models.TextField(null=True, blank=True)

    packed_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    dispatched_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    pending_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    palnning_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)

    packed_pieces = models.IntegerField(default=0, null=True)
    dispatched_pieces = models.IntegerField(default=0, null=True)
    pending_pieces = models.IntegerField(default=0, null=True)
    planning_pieces = models.IntegerField(default=0, null=True)

    die_over_weight = models.BooleanField(default=False)

    status = models.CharField(
        choices=STATUS_CHOICE, default="Pending", max_length=250, null=True
    )
    # Parallel process-tracking status (does not replace legacy `status`)
    process_status = models.CharField(
        choices=PROCESS_STAGE_CHOICES,
        default="WO_CREATED",
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
    )
    is_palnning = models.BooleanField(default=False)

    is_priority = models.BooleanField(default=False)
    priority_added_at = models.DateTimeField(null=True, blank=True)
    priority_added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="priority_added_workorders",
    )
    priority_removed_at = models.DateTimeField(null=True, blank=True)
    priority_removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="priority_removed_workorders",
    )

    def __str__(self):
        return f"{self.workorder.order_no} - {self.pieces}"

    class Meta:
        db_table = "workorder_detail"
        indexes = [
            models.Index(fields=["workorder", "deleted"], name="wod_wo_deleted_idx"),
            models.Index(fields=["deleted", "status"], name="wod_deleted_status_idx"),
            models.Index(
                fields=["workorder", "die_profile", "alloy", "temper", "length"],
                name="wod_lookup_idx",
            ),
            models.Index(fields=["status", "deleted"], name="wod_status_deleted_idx"),
            models.Index(
                fields=["is_priority", "status"], name="wod_priority_status_idx"
            ),
        ]

    @property
    def pending_pc(self):
        return (
            (self.pieces or 0)
            - (self.packed_pieces or 0)
            - (self.dispatched_pieces or 0)
        )

    @property
    def pending_wt(self):
        return (
            (self.net_weight or 0)
            - (self.packed_weight or 0)
            - (self.dispatched_weight or 0)
        )


class WorkOrderProcessTrack(BaseModule):
    """
    Process checklist for a WorkOrder item, optionally scoped to a Planning No.
    - planning=NULL  → item-level track
    - planning set   → planning-no track (same process list from Planning onward)
    """

    TRACK_SCOPE = (
        ("ITEM", "Item"),
        ("PLANNING", "Planning"),
    )

    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="process_tracks",
        db_index=True,
    )
    workorder_detail = models.ForeignKey(
        WorkOrderDetail,
        on_delete=models.CASCADE,
        related_name="process_tracks",
        db_index=True,
    )
    planning = models.ForeignKey(
        "planning.Planning",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_tracks",
        db_index=True,
    )
    scope = models.CharField(
        max_length=20, choices=TRACK_SCOPE, default="ITEM", db_index=True
    )
    current_stage = models.CharField(
        choices=PROCESS_STAGE_CHOICES,
        default="WO_CREATED",
        max_length=50,
        db_index=True,
    )
    requires_ageing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "workorder_process_track"
        indexes = [
            models.Index(
                fields=["workorder", "deleted", "scope"],
                name="wopt_wo_scope_idx",
            ),
            models.Index(
                fields=["workorder_detail", "deleted"],
                name="wopt_detail_idx",
            ),
            models.Index(
                fields=["planning", "deleted"],
                name="wopt_planning_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workorder_detail"],
                condition=models.Q(deleted=False, scope="ITEM", planning__isnull=True),
                name="uniq_item_process_track",
            ),
            models.UniqueConstraint(
                fields=["planning"],
                condition=models.Q(deleted=False, scope="PLANNING", planning__isnull=False),
                name="uniq_planning_process_track",
            ),
        ]

    def __str__(self):
        return f"{self.workorder_id}/{self.workorder_detail_id}/{self.scope}/{self.current_stage}"


class WorkOrderProcessStage(BaseModule):
    """Checkbox row for one process stage on a track."""

    track = models.ForeignKey(
        WorkOrderProcessTrack,
        on_delete=models.CASCADE,
        related_name="stages",
        db_index=True,
    )
    stage_code = models.CharField(
        choices=PROCESS_STAGE_CHOICES, max_length=50, db_index=True
    )
    stage_label = models.CharField(max_length=100)
    sequence = models.PositiveSmallIntegerField(default=0)
    is_applicable = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wo_process_stages_completed",
    )
    remarks = models.CharField(max_length=250, null=True, blank=True)

    class Meta:
        db_table = "workorder_process_stage"
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["track", "stage_code"], name="wops_track_stage_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["track", "stage_code"],
                condition=models.Q(deleted=False),
                name="uniq_track_stage_code",
            ),
        ]

    def __str__(self):
        return f"{self.track_id}:{self.stage_code}={'Y' if self.is_completed else 'N'}"

