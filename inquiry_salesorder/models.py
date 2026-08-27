import logging
import os

from django.conf import settings
from django.db import models
from django.forms import ValidationError
from customer.models import Customer
from die.models import Die
from common.models import JobWorkType, PackingMode
from inquiry.models import Inquiry
from product.models import Alloy, Temper
from utils.aws_file_upload import delete_uploaded_file, upload_doc_file

logger = logging.getLogger("file")


class InquirySalesOrder(models.Model):
    SALESORDER_STATUS_CHOICES = (
        ("SalesOrder", "SalesOrder"),
        ("WorkOrder", "WorkOrder"),
        (
            "Pending_Fixed_Rate_Approval", 
            "Pending_Fixed_Rate_Approval"
        )
    )
    ORDER_TYPE_CHOICES = (
        ("order", "Order"),
        ("trial", "Trial"),
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
    NALCO_TYPE_CHOICE = (
        ("Fixed", "Fixed"),
        ("Variable", "Variable"),
    )
    sales_order_no = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.SET_NULL,
        related_name="inquiry_sales_orders",
        null=True,
        blank=True,
    )
    order_date = models.DateField(auto_now_add=True)
    order_type = models.CharField(ORDER_TYPE_CHOICES, default="order", max_length=50)
    delivery_date = models.DateField(null=True, blank=True)
    purchase_order_no = models.CharField(max_length=30, null=True, blank=True)
    purchase_order_date = models.DateField(null=True, blank=True)
    project_name = models.CharField(max_length=255, null=True, blank=True)
    tolerance = models.CharField(
        choices=TOLERANCE_CHOICE, default="Zero(0)", max_length=100, null=True
    )
    nalco_type = models.CharField(
        choices=NALCO_TYPE_CHOICE, default="Variable", max_length=100, null=True
    )
    remarks = models.TextField(blank=True, null=True)
    packing_mode = models.ManyToManyField(
        PackingMode,
        related_name="inquiry_sales_orders",
        blank=True,
    )
    bill_to = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="inquiry_sales_orders",
        null=True,
        blank=True,
    )
    ship_to = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="inquiry_sales_orders_ship_to",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_sales_orders_approved_by",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_reason = models.TextField(null=True, blank=True)
    purchase_order_copy = models.CharField(max_length=255, blank=True, null=True)
    workorder_converted_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        choices=SALESORDER_STATUS_CHOICES, default="Pending_Fixed_Rate_Approval", max_length=100
    )
    terms_and_condition = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_sales_orders_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_sales_orders_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_sales_orders_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    def upload_doc(self, doc_dict: dict = {}):
        error_list = []
        logger.info("Document upload initiated with the following files: %s", doc_dict)
        allowed_types = [
            ".jpg",
            ".jpeg",
            ".png",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
        ]
        max_file_size = 2 * 1024 * 1024

        for attr, doc in doc_dict.items():
            if doc is not None:
                logger.info(f"Proccessing file for {attr} : {doc.name}")
                file_extension = os.path.splitext(doc.name)[1].lower()

                if file_extension not in allowed_types:
                    raise ValidationError(
                        {
                            attr: f"Invalid file type {file_extension} for {attr}. Allowed types are: {', '.join(allowed_types)}"
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
                    logger.error(f"Error uploading file for {attr}: {e}")
            else:
                logger.warning(f"No file provided for {attr}, skipping upload.")
        self.save()
        if error_list:
            raise ValidationError("upload_errors", error_list)

    class Meta:
        db_table = "inquiry_sales_order"
        permissions = [
            ("print_inquiry_salesorder", "Can print Inquiry Sales Order"),
            (
                "download_inquiry_salesorder_excel_copy",
                "Can download Inquiry Sales Order Excel",
            ),
            (
                "download_inquiry_salesorder_pdf_copy",
                "Can download Inquiry Sales Order PDF",
            ),
        ]

    def __str__(self):
        return (
            self.sales_order_no
            or self.purchase_order_number
            or f"Sales Order {self.id}"
        )


class InquirySalesOrderDetail(models.Model):
    SALESORDER_TYPES = (
        ("In_House", "In_House"),
        ("Job_Work", "Job_Work"),
    )
    inquiry_salesorder = models.ForeignKey(
        InquirySalesOrder,
        on_delete=models.CASCADE,
        related_name="inquiry_salesorder_details",
    )
    alloy = models.ForeignKey(Alloy, on_delete=models.CASCADE, null=True, blank=True)
    temper = models.ForeignKey(Temper, on_delete=models.CASCADE, null=True, blank=True)
    length = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    pieces = models.IntegerField(default=0, null=True, blank=True)
    net_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    max_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    min_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    salesorder_type = models.CharField(
        choices=SALESORDER_TYPES, default="In_House", max_length=50, null=True
    )
    surface_finish = models.ManyToManyField(
        JobWorkType,
        related_name="inquiry_salesorder_surface_finish",
        blank=True,
    )
    section_no = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inquiry_salesorder_section_no",
    )
    nalco_rate = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    modify_nalco_rate = models.BooleanField(default=False)
    nalco_rate_change_reason = models.TextField(null=True, blank=True)
    conversion = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    packing_cost = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    customer_reference_number = models.CharField(max_length=250, null=True, blank=True)
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
    anodising_description = models.CharField(max_length=250, null=True, blank=True)
    powder_coating_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    price_per_kg = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    powder_coating_description = models.CharField(max_length=250, null=True, blank=True)
    pvdf_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    pvdf_description = models.CharField(max_length=250, null=True, blank=True)
    laser_marking_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    laser_marking_description = models.CharField(max_length=250, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_salesorder_detail_created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_salesorder_detail_updated_by",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_salesorder_detail_deleted_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        order_ref = (
            self.inquiry_salesorder.sales_order_no
            or self.inquiry_salesorder.purchase_order_number
            or f"Order {self.inquiry_salesorder.id}"
        )
        return f"Detail for {order_ref}"

    class Meta:
        db_table = "inquiry_salesorder_detail"
        permissions = [
            ("print_inquiry_salesorder_detail", "Can print Inquiry Sales Order Detail"),
            (
                "download_inquiry_salesorder_detail_excel_copy",
                "Can download Inquiry Sales Order Detail Excel",
            ),
            (
                "download_inquiry_salesorder_detail_pdf_copy",
                "Can download Inquiry Sales Order Detail PDF",
            ),
        ]
