from django.db import models
from settings.models import BaseModule
from user.models import User


class CustomerType(BaseModule):
    name = models.CharField(max_length=255, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-id"]
        permissions = [
            ("download_customer_type_pdf_copy", "Can download customer type PDF"),
            ("download_customer_type_excel_copy", "Can download customer type Excel"),
        ]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
            models.Index(fields=["deleted"]),
            models.Index(fields=["deleted", "created_at"]),
        ]


class Customer(BaseModule):
    BUSINESS_TYPE = (
        ("INDIAN", "Indian"),
        ("OVERSEAS", "Overseas"),
    )

    COMPANY_TYPE = (
        ("customer", "customer"),
        ("vendor", "vendor"),
        ("customer_vendor", "customer_vendor"),
    )
    CUSTOMER_BALANCE = (
        ("credit", "credit"),
        ("debit", "debit"),
    )
    GST_TYPE_CHOICES = (("IGST", "IGST"), ("SGST_CGST", "SGST_CGST"))
    gstin_number = models.CharField(
        max_length=15, blank=True, null=True, unique=True, verbose_name="GSTIN Number"
    )
    gst_type = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="GST Type"
    )
    pan_number = models.CharField(
        max_length=10, blank=True, null=True, unique=True, verbose_name="PAN Number"
    )
    customer_name = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Customer Name",
        db_index=True,
    )
    person_name = models.CharField(max_length=250, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone_number = models.CharField(max_length=15, verbose_name="Phone Number")
    customer_type = models.ForeignKey(
        "CustomerType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Customer Type",
    )
    delivery_days = models.IntegerField(
        blank=True, null=True, verbose_name="Delivery Days"
    )
    udyam_no = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Udyam No / MSME",
    )
    applicable_gst = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=GST_TYPE_CHOICES,
        verbose_name="Applicable GST",
    )
    office_address_shop = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Office Address - Shop No, Building, Apartment",
    )
    office_address_area = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Office Address - Area, Street",
    )
    office_address_landmark = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Office Address - Landmark"
    )
    office_address_pin_code = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Office Address - Pin Code"
    )
    office_address_city = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Office Address - City"
    )
    office_address_state = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Office Address - State"
    )
    office_address_country = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Office Address - Country"
    )

    factory_address_shop = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Factory Address - Shop No, Building, Apartment",
    )
    factory_address_area = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Factory Address - Area, Street",
    )
    factory_address_landmark = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Factory Address - Landmark"
    )
    factory_address_pin_code = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Factory Address - Pin Code"
    )
    factory_address_city = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Factory Address - City"
    )
    factory_address_state = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Factory Address - State"
    )
    factory_address_country = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Factory Address - Country"
    )
    sales_executive = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_executive",
    )
    sales_executive_assistant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_executive_assistant",
    )
    business_type = models.CharField(
        choices=BUSINESS_TYPE, max_length=15, default="INDIAN"
    )
    import_export_code = models.CharField(max_length=50, blank=True, null=True)
    beneficiary_agent_code = models.CharField(max_length=50, blank=True, null=True)
    trade_name = models.CharField(max_length=100, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    fax_number = models.CharField(max_length=15, blank=True, null=True)
    website = models.CharField(blank=True, null=True)
    is_company_visible_on_documents = models.BooleanField(default=False)
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    due_days = models.IntegerField(null=True, blank=True)
    licence_no = models.CharField(max_length=100, unique=True, blank=True, null=True)
    note = models.TextField(null=True, blank=True)
    customer_balance = models.CharField(
        choices=CUSTOMER_BALANCE, max_length=10, null=True, blank=True, default="credit"
    )
    amount = models.CharField(max_length=250, blank=True, null=True)
    company_type = models.CharField(
        choices=COMPANY_TYPE, max_length=50, null=True, blank=True, default="customer"
    )

    def __str__(self):
        return f"{self.customer_name} - {self.person_name}"

    class Meta:
        permissions = [
            (
                "print_customer_workorder_report_pdf_copy",
                "Can print customer workorder report",
            ),
            ("download_customer_pdf_copy", "Can download customer PDF"),
            ("download_customer_excel_copy", "Can download customer Excel"),
        ]
        indexes = [
            models.Index(fields=["customer_type"]),
            models.Index(fields=["sales_executive"]),
            models.Index(fields=["sales_executive_assistant"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
            models.Index(fields=["deleted"]),
            models.Index(fields=["company_type"]),
            models.Index(fields=["gstin_number"]),
            models.Index(fields=["pan_number"]),
            models.Index(fields=["deleted", "company_type"]),
            models.Index(fields=["deleted", "created_at"]),
        ]


class ContactPerson(BaseModule):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="contact_persons"
    )
    contact_person_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Contact Person Name"
    )
    contact_person_designation = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Contact Person Designation"
    )
    contact_person_mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Contact Person Mobile Number",
    )
    contact_person_email = models.EmailField(
        blank=True, null=True, verbose_name="Contact Person Email"
    )

    def __str__(self):
        return f"{self.contact_person_name} ({self.customer.customer_name})"


class BankingDetails(BaseModule):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="banking_details"
    )
    bank_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Bank Name"
    )
    bank_account_number = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Bank Account Number"
    )
    bank_ifsc_code = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="Bank IFSC Code"
    )
    bank_branch_address = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Branch Address"
    )
    beneficiary_swift_code = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Beneficiary Swift Code"
    )
    bank_ad_code = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Bank AD Code"
    )

    def __str__(self):
        return f"{self.bank_name} ({self.customer.customer_name})"

    class Meta:
        unique_together = [["bank_account_number"]]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["deleted"]),
            models.Index(fields=["customer", "deleted"]),
        ]
