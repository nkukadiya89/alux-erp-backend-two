from django.conf import settings
from django.db import models


class ShiftMaster(models.Model):
    shift_name = models.CharField(max_length=20, db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="shiftmaster_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="shiftmaster_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "shift_master"

    def __str__(self):
        return self.shift_name if self.shift_name else "Shift Master"


class ShiftSnapshotMixin(models.Model):
    shift = models.ForeignKey(
        ShiftMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_shift",
    )
    shift_name_snapshot = models.CharField(max_length=50, null=True, blank=True)
    shift_start_snapshot = models.TimeField(null=True, blank=True)
    shift_end_snapshot = models.TimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def capture_shift_snapshot(self, shift):
        if shift:
            self.shift = shift
            self.shift_name_snapshot = shift.shift_name
            self.shift_start_snapshot = shift.start_time
            self.shift_end_snapshot = shift.end_time
