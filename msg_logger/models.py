from django.db import models

# from user.models import User

# Create your models here.


class LogActivity(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("ARCHIVE", "Archive"),
        ("RESTORE", "Restore"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("PRINT", "Print"),
        ("DOWNLOAD", "Download"),
        ("CONVERT", "Convert"),
        ("SHIFT BUNDLE", "Shift Bundle"),
        ("VERIFY", "Verify"),
        ("FINALIZE BUNDLE", "Finalize Bundle"),
    ]

    action = models.CharField(max_length=20, choices=ACTION_CHOICES, null=True)
    action_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    module_name = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.CharField(max_length=50, null=True, blank=True)
    discription = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    payload = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_action_display()} by {self.action_by} on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        db_table = "log_activity"
        ordering = ["-timestamp"]
