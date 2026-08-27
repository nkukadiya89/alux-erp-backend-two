from django.db import models
from django.conf import settings
from shift.models import ShiftSnapshotMixin
from die.models import DiePress
from settings.models import BaseModule


class ShiftLog(BaseModule, ShiftSnapshotMixin):
    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Submitted", "Submitted"),
    ]
    date = models.DateField()
    press = models.ForeignKey(
        DiePress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shiftlog_press",
    )

    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shiftlog_supervisor",
        null=True,
        blank=True,
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Draft")

    def __str__(self):
        return f"{self.date} - {self.shift} - {self.press}"


