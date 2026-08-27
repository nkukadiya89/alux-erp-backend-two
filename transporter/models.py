from django.db import models

from settings.models import BaseModule

class Transporter(BaseModule):
    BALANCE_CHOICES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    SEND_SMS_CHOICES = [
        ("sms", "Sms"),
        ("email", "Email"),
        ("whatsapp", "Whatsapp"),
    ]

    STATUS = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    party_name = models.CharField(
        max_length=200, null=True, blank=True, db_index=True, unique=True
    )
    party_code = models.CharField(
        max_length=100, null=True, blank=True, db_index=True, unique=True
    )
    opening_balance = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    balance_type = models.CharField(
        max_length=10, choices=BALANCE_CHOICES, default="credit"
    )
    is_cash_amount = models.BooleanField(default=False)
    address = models.CharField(max_length=300, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    pincode = models.CharField(max_length=30, null=True, blank=True)
    mobile_no_sms = models.CharField(max_length=20, null=True, blank=True)
    mobile_no = models.CharField(
        max_length=20, null=True, blank=True, db_index=True, unique=True
    )
    phone_no = models.CharField(max_length=50, null=True, blank=True)
    email_id = models.EmailField(max_length=50, null=True, blank=True)
    send_sms_type = models.CharField(
        max_length=20, choices=SEND_SMS_CHOICES, default="sms"
    )
    is_active = models.CharField(max_length=20, choices=STATUS, default="inactive")

    def __str__(self):
        return f"{self.party_name}"

    class Meta:
        db_table = "transporter"
        indexes = [
            models.Index(fields=["deleted", "is_active"]),
            models.Index(fields=["deleted", "-id"]),
            models.Index(fields=["deleted", "created_at"]),
            models.Index(fields=["deleted", "updated_at"]),
        ]

        permissions = [
            ("download_transporter_excel_copy", "Can download transporter Excel"),
            ("download_transporter_pdf_copy", "Can download transporter PDF"),
        ]
