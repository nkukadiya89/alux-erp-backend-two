from django.db import models
from django.forms import ValidationError
from settings.models import BaseModule
from utils.aws_file_upload import delete_uploaded_file, upload_doc_file


class BlosterType(BaseModule):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return self.name


class BlosterMaster(BaseModule):
    bloster_no = models.CharField(max_length=100)
    bloster_image = models.CharField(max_length=250, null=True, blank=True)
    press = models.ForeignKey(
        "die.DiePress", on_delete=models.CASCADE, null=True, blank=True
    )
    type = models.ForeignKey(
        BlosterType, on_delete=models.CASCADE, null=True, blank=True
    )
    diameter_mm = models.IntegerField(null=True, blank=True)
    thickness_mm = models.IntegerField(null=True, blank=True)
    size = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    autocard = models.CharField(max_length=250, null=True)
    pdf = models.CharField(max_length=250, null=True)

    def __str__(self):
        return f"{self.bloster_no}"

    class Meta:
        unique_together = ["bloster_no"]
        permissions = [
            ("download_bolster_pdf_copy", "Can download bolster PDF"),
            ("download_bolster_excel_copy", "Can download bolster Excel"),
        ]

    def upload_doc(self, doc_list: list = []):
        error_list = []
        MAX_FILE_SIZE = 2 * 1024 * 1024

        attributes = [
            ("bloster_image", [".pdf", ".jpg", ".jpeg", ".png"]),
            ("autocard", [".dwg"]),
            ("pdf", [".pdf"]),
        ]

        for (attr, allowed_types), doc in zip(attributes, doc_list):

            if doc:
                if doc.size > MAX_FILE_SIZE:
                    raise ValidationError(
                        f"File size too large for {attr}. Maximum allowed size is 2 MB."
                    )
                current_value = None
                if attr == "bloster_image":
                    current_value = self.bloster_image
                elif attr == "autocard":
                    current_value = self.autocard
                elif attr == "pdf":
                    current_value = self.pdf

                try:
                    if current_value:
                        delete_uploaded_file(current_value)
                    new_value, _ = upload_doc_file(
                        doc, allowed_types, "BlosterMaster/", self.id, None
                    )

                    if attr == "bloster_image":
                        self.bloster_image = new_value
                    elif attr == "autocard":
                        self.autocard = new_value
                    elif attr == "pdf":
                        self.pdf = new_value

                except Exception as e:
                    error_list.append(attr)

            else:
                if self._state.adding:
                    if attr == "bloster_image":
                        delete_uploaded_file(self.bloster_image)
                        self.bloster_image = None
                    elif attr == "autocard":
                        delete_uploaded_file(self.autocard)
                        self.autocard = None
                    elif attr == "pdf":
                        delete_uploaded_file(self.pdf)
                        self.pdf = None

        self.save()
        if error_list:
            return f"Error processing files: {error_list}"
