import uuid

from django.db import models

from common.models import BaseModel
from user.models import User


class ImportJob(BaseModel):
    """Main import job tracking"""

    JOB_STATUS = (
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    )

    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    model_name = models.CharField(max_length=100)  # 'customer', 'item', 'vendor', etc.
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    status = models.CharField(choices=JOB_STATUS, max_length=20, default="PENDING")
    total_records = models.IntegerField(default=0)
    processed_records = models.IntegerField(default=0)
    success_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    error_summary = models.JSONField(default=dict)
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.model_name} - {self.job_id}"

    class Meta:
        db_table = "bulk_import_job"


class ImportRecord(BaseModel):
    """Individual record import tracking"""

    import_job = models.ForeignKey(
        ImportJob, on_delete=models.CASCADE, related_name="import_records"
    )
    row_number = models.IntegerField()
    raw_data = models.JSONField()
    processed_data = models.JSONField(null=True)
    is_success = models.BooleanField(default=False)
    error_details = models.JSONField(default=dict)
    action_taken = models.CharField(max_length=20, default="SKIP")  # INSERT/UPDATE/SKIP
    created_instance_id = models.IntegerField(null=True)

    def __str__(self):
        return f"{self.import_job.job_id} - Row {self.row_number}"

    class Meta:
        # db_table = 'bulk_import_record'
        indexes = [
            models.Index(fields=["import_job", "row_number"]),
            models.Index(fields=["import_job", "is_success"]),
        ]


class ImportLog(BaseModel):
    """Import log for tracking bulk imports"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    master = models.CharField(max_length=50)  # Model name
    total = models.IntegerField()
    success = models.IntegerField()
    failed = models.IntegerField()
    file_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.master} - {self.file_name}"

    class Meta:
        db_table = "bulk_import_log"


class ImportErrorRow(BaseModel):
    """Individual error records for import"""

    log = models.ForeignKey(ImportLog, on_delete=models.CASCADE, related_name="errors")
    row_number = models.IntegerField()
    error = models.TextField()
    row_data = models.JSONField(default=dict)

    def __str__(self):
        return f"Row {self.row_number} - {self.log.master}"

    class Meta:
        db_table = "bulk_import_error_row"
