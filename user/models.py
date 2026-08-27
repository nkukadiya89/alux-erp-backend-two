import os

from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import BaseModel
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket

# Create your models here.


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """User model."""

    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, default="")
    last_login = models.DateTimeField(_("last login"), null=True)
    email = models.EmailField(_("email address"), unique=True)
    otp = models.IntegerField(null=True)
    whatsapp_otp = models.IntegerField(null=True)
    phone = models.CharField(max_length=15, null=True)
    is_active = models.BooleanField(default=False)
    status = models.CharField(choices=STATUS_CHOICES, default="inactive", max_length=25)
    keep_me_logged_in = models.BooleanField(default=False)
    profile_image = models.CharField(max_length=250, null=True)
    is_varified = models.BooleanField(default=False)
    full_name = models.CharField(max_length=201, null=True, blank=True, db_index=True)

    objects = UserManager()  # type: ignore

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"
        ordering = ["-id"]
        permissions = [
            ("download_user_pdf_copy", "Can download user PDF"),
            ("download_user_excel_copy", "Can download user Excel"),
        ]

    def upload_profile_image(self, profile_image_file):
        """
        Uploads a profile image to the file storage for the given instance.
        The image can be of type .jpg, .jpeg, or .png and will be uploaded to the "Die" folder
        under the instance's ID. If a file already exists, it will be deleted and replaced
        with the new one.

        :param profile_image: Name of the profile image attribute on the instance.
        :return: None or a string indicating the error.
        """
        allowed_types = [".jpg", ".jpeg", ".png"]
        error_list = []

        file_extension = os.path.splitext(profile_image_file.name)[1].lower()
        if file_extension not in allowed_types:
            return f"Invalid file type: {file_extension}. Allowed types are {', '.join(allowed_types)}."

        # Retrieve the current value of the profile_image attribute
        current_value = getattr(self, "profile_image", None)

        try:
            # Delete the existing file if it exists
            if current_value:
                delete_uploaded_file(current_value)

            # Upload the new file
            new_value, _ = upload_file_to_bucket(profile_image_file, allowed_types, "ProfileImage/", self.id, None)  # type: ignore
            setattr(self, "profile_image", new_value)
            print("file uploaded")
        except Exception as e:
            print(str(e))
            error_list.append("profile_image")

            # If the instance is new and still being added, clean up
            if self._state.adding and current_value:
                delete_uploaded_file(current_value)
                setattr(self, "profile_image", None)

        # Save the instance after updating the attribute
        self.save()

        # Return error messages if any occurred
        if error_list:
            return f"Error processing files: {error_list}"

    def save(self, *args, **kwargs):
        self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)

    @property
    def full_name_property(self):
        return f"{self.first_name} {self.last_name}".strip()


class UserProfile(BaseModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="user_profile"
    )
    profile_image = models.CharField(max_length=250, null=True)
    designation = models.CharField(max_length=30, null=True)
    message = models.CharField(max_length=200, default="")
    role = models.CharField(max_length=15, null=True)
    whatsapp_verified = models.BooleanField(default=False)
    aadhar_card = models.CharField(max_length=12, null=True)
    pancard = models.CharField(max_length=10, null=True)
    emergency_contact = models.CharField(max_length=15, null=True)
    current_address = models.CharField(max_length=150, null=True)
    permanent_address = models.CharField(max_length=150, null=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    password_last_changed = models.DateTimeField(null=True)

    class Meta:
        db_table = "user_profile"
        ordering = ["-id"]


# No need to show permissions
class AuthGroupModel(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)

    class Meta:
        db_table = "auth_group"
        managed = False


# No need to show permissions
class ContentTypeModel(BaseModel):
    id = models.AutoField(primary_key=True)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        db_table = "django_content_type"
        managed = False


# No need to show permissions
class AuthPermissionModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentTypeModel, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "auth_permission"
        managed = False


# No need to show permissions
class AuthGroupPermissionsModel(models.Model):
    id = models.AutoField(primary_key=True)
    group = models.ForeignKey(AuthGroupModel, on_delete=models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermissionModel, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "auth_group_permissions"
        managed = False


# No need to show permissions
class UserGroupsModel(BaseModel):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(AuthGroupModel, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "user_groups"
        managed = False


class CustomGroup(Group):
    sequence = models.PositiveIntegerField()
    group_name = models.CharField(max_length=150, null=True)

    created_by = models.ForeignKey(
        User,
        related_name="created_custom_groups",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        User,
        related_name="updated_custom_groups",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(null=True)
    deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.sequence is None:
            last_record = (
                CustomGroup.objects.filter(created_by=self.created_by)
                .order_by("-sequence")
                .first()
            )
            self.sequence = (last_record.sequence + 1) if last_record else 1
        super(CustomGroup, self).save(*args, **kwargs)
