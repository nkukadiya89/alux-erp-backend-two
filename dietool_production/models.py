from django.db import models
from product.models import Alloy, Temper
from settings.models import BaseModule
from shift.models import ShiftSnapshotMixin
from die.models import Die, DieTool, DiePress
from production.models import Production
from melting_furnace.models import Furnace
from user.models import User
from multiselectfield import MultiSelectField
from django.conf import settings

class DieProductionLog(BaseModule, ShiftSnapshotMixin):
    die_tool = models.ForeignKey(DieTool, on_delete=models.CASCADE, null=True, related_name="productions_dietool")
    date = models.DateField(null=True, blank=True)
    press = models.ForeignKey(DiePress, on_delete=models.CASCADE, null=True, related_name="productions_press")
    production_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.die_tool.tool_number} - {self.date}"

    class Meta:
        db_table = "die_production_log"

        permissions = [
            ("download_die_production_log_excel_copy", "Can download Die Production Log Excel"),
            ("download_die_production_log_pdf_copy", "Can download Die Production Log PDF"),
        ]

class MaintenanceType(BaseModule):
    name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "maintenance_type"

class ReasonForMaintenance(BaseModule):
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "reason_for_maintenance"

class DieMaintenanceLog(BaseModule):
    INSPECTION_TYPE_CHOICES = (
        ('visual', 'Visual Inspection'),
        ('dimensional', 'Dimensional Inspection'),
        ('hardness', 'Hardness Test'),
        ('surface', 'Surface Finish Check'),
        ('crack', 'Crack Detection'),
        ('trial', 'Trial Run Inspection'),
        ('final', 'Final QC Inspection'),
    )
    INSPECTION_RESULT_CHOICES = (
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('rework', 'Rework Required'),
        ('deviation', 'Accepted with Deviation'),
        ('hold', 'Hold'),
        ('rejected', 'Rejected'),
    )
    die_tool = models.ForeignKey(DieTool, on_delete=models.CASCADE, null=True, related_name="maintenance_dietool")
    date = models.DateField(null=True, blank=True)
    die_life_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    maintenance_type = models.ForeignKey(
        MaintenanceType, on_delete=models.CASCADE, null=True, related_name="maintenance_log"
    )
    reason_for_maintenance = models.ForeignKey(
        ReasonForMaintenance,
        on_delete=models.CASCADE,
        null=True,
        related_name="maintenancehistory_reason",
    )
    inspection_type = models.CharField(max_length=20, choices=INSPECTION_TYPE_CHOICES, null=True)
    inspection_result  = models.CharField(max_length=20, choices=INSPECTION_RESULT_CHOICES, null=True)
    inspection_done_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, related_name="maintenance_inspector")
    after_maintenance_done_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, related_name="after_maintenance_done_by_user")
    hardness_before = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hardness_after = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.die_tool.tool_number} - {self.date}"

    class Meta:
        db_table = "die_maintenance_log"

        permissions = [
            ("download_die_tool_maintenance_excel_copy", "Can download Die Tool maintenance Excel"),
            ("download_die_tool_maintenance_pdf_copy", "Can download Die Tool maintenance PDF"),
        ]

class DieNitridingBatch(BaseModule, ShiftSnapshotMixin):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    batch_no = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    furnace = models.ForeignKey(
        Furnace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="die_nitriding_batches",
    )

    date = models.DateField(null=True, blank=True)

    nitriding_start_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    holding_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    blower_start_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    nitriding_stop_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nitriding_batches_operator",
    )

    total_die_weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    nitriding_start_gas_weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    nitriding_stop_gas_weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    actual_used_ammonia_gas = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    remarks = models.TextField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.batch_no or f"Nitriding Batch {self.pk}"

    class Meta:
        db_table = "die_nitriding_batch"
        ordering = ["-id"]

        permissions = [
            (
                "download_nitriding_batch_excel_copy",
                "Can download Nitriding Batch Excel",
            ),
            (
                "download_nitriding_batch_pdf_copy",
                "Can download Nitriding Batch PDF",
            ),
        ]


class DieNitridingBatchDetail(BaseModule):
    batch = models.ForeignKey(
        DieNitridingBatch,
        on_delete=models.CASCADE,
        related_name="details",
    )

    section = models.ForeignKey(
        Die,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="die_nitriding_batch_details",
    )

    die_tool = models.ForeignKey(
        DieTool,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nitriding_batch_details",
    )

    # Checkbox selected -> ID save
    die_plate = models.BooleanField(default=False)

    # Checkbox selected -> ID save
    die_mandrel = models.BooleanField(default=False)

    die_weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.batch.batch_no} - {self.pk}"

    class Meta:
        db_table = "die_nitriding_batch_detail"
        ordering = ["id"]

class DieTrialLog(BaseModule, ShiftSnapshotMixin):

    RESULT_CHOICES = [
        ("ok", "ok"),
        ("not_ok", "not_ok"),
        ('approved', 'Approved'),
        ('not_approved', 'Not Approved'),
        ('deviation', 'Approved with Deviation'),
        ('rework', 'Rework Required'),
        ('hold', 'Hold'),
    ]

    TRIAL_TYPE_CHOICES = (
        ('new', 'New Die Trial'),
        ('correction', 'Correction Trial'),
        ('repeat', 'Repeat Trial'),
        ('development', 'Development Trial'),
        ('approval', 'Customer Approval Trial'),
    )

    die_tool = models.ForeignKey(DieTool, on_delete=models.CASCADE, null=True, related_name="dietriallog_dietool")
    production = models.ForeignKey(Production, on_delete=models.CASCADE, null=True, related_name="dietriallog_production")
    trial_date = models.DateField(null=True, blank=True)
    trial_no = models.CharField(max_length=255, null=True, blank=True)
    trial_type = models.CharField(max_length=20, choices=TRIAL_TYPE_CHOICES, null=True)
    alloy = models.ForeignKey(Alloy, on_delete=models.SET_NULL, null=True, related_name="dietriallog_alloy")
    temper = models.ForeignKey(Temper, on_delete=models.SET_NULL, null=True, related_name="dietriallog_temper")
    billet_size = models.IntegerField(null=True, blank=True)
    suggestion = models.TextField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="dietriallog_approver")
    total_extrude_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    trial_count = models.IntegerField(null=True, blank=True)
    result = models.CharField(max_length=30, choices=RESULT_CHOICES, null=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.die_tool.tool_number} - {self.trial_date}"

    class Meta:
        db_table = "die_trial_log"

        permissions = [
            ("download_die_trial_log_excel_copy", "Can download Die Trial log Excel"),
            ("download_die_trial_log_pdf_copy", "Can download Die Trial log PDF"),
        ]


class CorrectionType(BaseModule):
    name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "correction_type"


class ReasonForCorrection(BaseModule):
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "reason_for_correction"

class CorrectionInspectionType(BaseModule):
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "correction_inspection_type"


class ActivityMaster(BaseModule):
    name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "activity_master"


class CorrectionHistory(BaseModule):
    die_tool = models.ForeignKey(DieTool, on_delete=models.CASCADE, null=True, related_name="correctionhistory_dietool")
    date = models.DateField(null=True, blank=True)
    correction_type = models.ForeignKey(
        CorrectionType,
        on_delete=models.CASCADE,
        null=True,
        related_name="correctionhistory_correctiontype",
    )
    problem_description = models.TextField(null=True, blank=True)
    correction_request_no = models.CharField(max_length=255, null=True, blank=True)
    inspection_type = models.ForeignKey(
        CorrectionInspectionType,
        on_delete=models.CASCADE,
        null=True,
        related_name="correctionhistory_inspectiontype",
    )
    inspection_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="correction_inspected_by_user",
    )
    inspection_result = models.TextField(null=True, blank=True)
    reason_for_correction = models.ForeignKey(
        ReasonForCorrection,
        on_delete=models.CASCADE,
        null=True,
        related_name="correctionhistory_reason",
    )
    correction_done_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, related_name="correction_done_by_user")
    die_life_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    activity = models.ManyToManyField(
        ActivityMaster,
        blank=True,
        related_name="correctionhistory_activity",
    )
    result = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.die_tool.tool_number if self.die_tool else 'N/A'} - {self.date}"

    class Meta:
        db_table = "die_correction_history"

        permissions = [
            ("download_die_correction_history_excel_copy", "Can download Die Correction History Excel"),
            ("download_die_correction_history_pdf_copy", "Can download Die Correction History PDF"),
        ]


class AnalysisMethod(BaseModule):
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "analysis_method"


class DieFailureLog(BaseModule, ShiftSnapshotMixin):
    FAILURE_TYPE = (
        ('breakdown', 'Breakdown'),
        ('crack', 'Crack'),
        ('wear', 'Wear'),
        ('scrap', 'Scrap'),
    )
    SOURCE_CHOICES = (
        ('production', 'Production'),
        ('maintenance', 'Maintenance'),
        ('trial', 'Trial'),
        ('manual', 'Manual'),
    )
    SEVERITY_CHOICES = (
        ("minor", "Minor"),
        ("major", "Major"),
        ("critical", "Critical"),
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
    die_tool = models.ForeignKey(DieTool, on_delete=models. CASCADE, null=True, related_name='failure_log_dietool')
    failure_no = models.CharField(max_length=255, null=True, blank=True)
    failure_date = models.DateField(null=True, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, null=True)
    summary = models.TextField(null=True, blank=True)
    analysis_method = models.ForeignKey(AnalysisMethod, on_delete=models.SET_NULL, null=True, related_name="failurelog_analysis")
    failure_type = models.CharField(max_length=20, choices=FAILURE_TYPE, null=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, null=True)
    broken_part = MultiSelectField(choices=BROKEN_PART_CHOICES, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    root_cause = models.TextField(null=True, blank=True)
    action_taken = models.TextField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    downtime_hours = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.die_tool.tool_number if self.die_tool else 'N/A'} - {self.failure_date}"
    
    class Meta:
        db_table = "die_failure_log"

        permissions = [
            ("download_die_failure_log_excel_copy", "Can download Die Failure Log Excel"),
            ("download_die_failure_log_pdf_copy", "Can download Die Failure Log PDF"),
        ]
