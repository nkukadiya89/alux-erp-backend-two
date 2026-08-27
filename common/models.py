import logging
import uuid
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from settings.models import BaseModule
from utils.log_activity import log_user_activity

logger = logging.getLogger("file")


class ArchiveMixin(ModelViewSet):

    @action(methods=["get"], detail=False, url_path="archive-list")
    def archive_list(self, request, *args, **kwargs):
        logger.info("Fetching archived items.")
        queryset = self.get_queryset().filter(deleted=True).order_by("-deleted_at")
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.info("Archived items fetched successfully.")
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        logger.info("Archived items fetched successfully.")
        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def unarchive(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance.deleted:
            return Response(
                {"message": "Already unarchived"}, status=status.HTTP_400_BAD_REQUEST
            )

        update_kwargs = {"deleted": False}
        if hasattr(instance, "deleted_at"):
            update_kwargs["deleted_at"] = None
        if hasattr(instance, "deleted_by"):
            update_kwargs["deleted_by"] = None
        instance.__class__.objects.filter(pk=instance.pk).update(**update_kwargs)

        log_user_activity(
            user=request.user,
            action="RESTORE",
            module_name=instance.__class__.__name__,
            description=f"Restore {self.queryset.model.__name__} -  {self.get_instance_display(instance)}",
            request=request,
        )

        return Response(
            {"success": True, "message": "Record Unarchived successfully"},
            status=status.HTTP_200_OK,
        )
    
    @action(methods=["post"], detail=False, url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        if not ids or not isinstance(ids, list):
            return Response(
                {"message": "A non-empty list of 'ids' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(pk__in=ids, deleted=False)
        found_ids = list(queryset.values_list("pk", flat=True))

        if not found_ids:
            return Response(
                {"message": "No active records found for the provided IDs."},
                status=status.HTTP_404_NOT_FOUND,
            )

        update_kwargs = {"deleted": True}

        if hasattr(queryset.model, "deleted_at"):
            from django.utils import timezone
            update_kwargs["deleted_at"] = timezone.now()

        if hasattr(queryset.model, "deleted_by"):
            update_kwargs["deleted_by"] = request.user

        queryset.update(**update_kwargs)

        logger.info(
            f"Bulk archived {len(found_ids)} {queryset.model.__name__} records: {found_ids}"
        )

        for instance in self.get_queryset().filter(pk__in=found_ids):
            log_user_activity(
                user=request.user,
                action="ARCHIVE",
                module_name=instance.__class__.__name__,
                description=f"Bulk Archive {queryset.model.__name__} - {self.get_instance_display(instance)}",
                request=request,
            )

        not_found_ids = list(set(ids) - set(found_ids))

        return Response(
            {
                "success": True,
                "message": f"{len(found_ids)} record(s) archived successfully.",
                "archived_ids": found_ids,
                **({"skipped_ids": not_found_ids} if not_found_ids else {}),
            },
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=False, url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        if not ids or not isinstance(ids, list):
            return Response(
                {"message": "A non-empty list of 'ids' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(pk__in=ids, deleted=True)
        found_ids = list(queryset.values_list("pk", flat=True))

        if not found_ids:
            return Response(
                {"message": "No archived records found for the provided IDs."},
                status=status.HTTP_404_NOT_FOUND,
            )

        update_kwargs = {"deleted": False}

        if hasattr(queryset.model, "deleted_at"):
            update_kwargs["deleted_at"] = None

        if hasattr(queryset.model, "deleted_by"):
            update_kwargs["deleted_by"] = None

        queryset.update(**update_kwargs)

        logger.info(
            f"Bulk unarchived {len(found_ids)} {queryset.model.__name__} records: {found_ids}"
        )

        for instance in self.get_queryset().filter(pk__in=found_ids):
            log_user_activity(
                user=request.user,
                action="RESTORE",
                module_name=instance.__class__.__name__,
                description=f"Bulk Restore {queryset.model.__name__} - {self.get_instance_display(instance)}",
                request=request,
            )

        not_found_ids = list(set(ids) - set(found_ids))

        return Response(
            {
                "success": True,
                "message": f"{len(found_ids)} record(s) unarchived successfully.",
                "unarchived_ids": found_ids,
                **({"skipped_ids": not_found_ids} if not_found_ids else {}),
            },
            status=status.HTTP_200_OK,
        )


class AllobjectsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)


class InactiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=True)


class RejectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(approve=False, reject=True)


class ApproveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(approve=True, reject=False)


class BaseModel(models.Model):
    f_id = models.IntegerField(default=0)
    approve = models.BooleanField(default=False)
    reject = models.BooleanField(default=False)
    approve_remarks = models.TextField(null=True)
    done_flag = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_updated_by",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True)
    approved_by = models.IntegerField(default=0)

    objects = AllobjectsManager()
    active_object = ActiveManager()
    deleted_object = InactiveManager()
    approved_object = ApproveManager()
    rejected_object = RejectManager()

    class Meta:
        abstract = True

    @property
    def created_by_info(self):

        created_by = self.created_by
        if created_by:
            return {"id": created_by.id, "name": created_by.get_full_name()}
        return None

    def save(self, *args, **kwargs):
        # Use _state.adding so models with default PK (e.g. UUID) are treated as new on first save
        is_new = self._state.adding
        user = kwargs.pop("user", None)
        if is_new:
            # New record: never set updated_at/updated_by (only set on actual updates)
            self.updated_at = None
            if user and not self.created_by:
                self.created_by = user
        else:
            # Existing record: set updated_at (and updated_by if user provided)
            self.updated_at = timezone.now()
            if user:
                self.updated_by = user

        unique_fields = getattr(self, "unique_fields", None)
        if unique_fields:
            filters = {field: getattr(self, field) for field in unique_fields}
            if self.__class__.objects.filter(**filters).exists():
                raise ValueError(
                    f"Duplicate entry exists for unique fields: {unique_fields}"
                )
        super().save(*args, **kwargs)


class FinancialYearModel(BaseModel):
    fid = models.AutoField(primary_key=True)
    financial_year = models.CharField(max_length=15, default="")
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(default=date.today)
    default = models.BooleanField(default=False)
    current = models.BooleanField(default=False)

    def __str__(self):

        return f"{self.fid} - {self.financial_year}"

    class Meta:
        db_table = "financial_year"

    def save(self, *args, **kwargs):
        if not self.start_date or not self.end_date:
            super().save(*args, **kwargs)
            return

        today = date.today()
        if self.start_date <= today <= self.end_date:
            FinancialYearModel.objects.filter(default=True).update(default=False)
            self.default = True
        else:
            self.default = False

        super().save(*args, **kwargs)


class Country(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True)
    unicode = models.CharField(max_length=80, unique=True)
    country_flag = models.URLField(max_length=200)
    phone_code = models.CharField(max_length=5, null=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "country"


class Currency(BaseModel):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    currency_name = models.CharField(max_length=200)
    currency_code = models.CharField(max_length=200)
    currency_symbol = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.currency_name} - {self.currency_symbol}"

    class Meta:
        db_table = "currency"


class GstType(BaseModel):
    name = models.CharField(max_length=10, unique=True)
    full_name = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = "GstType"

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"


class JobWorkType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    discription = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "jobwork_type"


class PackingMode(BaseModule):
    code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "packing_mode"
        permissions = [
            ("download_packing_mode_pdf_copy", "Can download packing_mode PDF"),
            ("download_packing_mode_excel_copy", "Can download packing_mode Excel"),
        ]


class PlantType(BaseModule):
    """
    Plant Type Master - Defines types of plants (EXTRUSION, WAREHOUSE, SITE, OFFICE, etc.)
    """

    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Uppercase code like EXTRUSION, WAREHOUSE",
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "plant_type"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_deleted", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(is_deleted=False),
                name="unique_active_plant_type_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)


class PlantCapability(BaseModule):
    """
    Plant Capability Master - Defines WHAT ACTIONS are allowed (PRODUCTION, INVENTORY, DISPATCH, etc.)
    """

    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Uppercase code like PRODUCTION, INVENTORY",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "plant_capability"
        ordering = ["code"]
        verbose_name = "Plant Capability"
        verbose_name_plural = "Plant Capabilities"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_deleted", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(is_deleted=False),
                name="unique_active_plant_capability_code",
            ),
        ]
        permissions = [
            ("download_plant_type_pdf_copy", "Can download plant type PDF"),
            ("download_plant_type_excel_copy", "Can download plant type Excel"),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)


class PlantTypeCapability(BaseModule):
    """
    Many-to-Many mapping between PlantType and PlantCapability
    Defines which capabilities are available for each plant type
    """

    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plant_type = models.ForeignKey(
        PlantType, on_delete=models.PROTECT, related_name="capabilities", db_index=True
    )
    capability = models.ForeignKey(
        PlantCapability,
        on_delete=models.PROTECT,
        related_name="plant_types",
        db_index=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "plant_type_capability"
        ordering = ["plant_type__code", "capability__code"]
        verbose_name = "Plant Type Capability"
        verbose_name_plural = "Plant Type Capabilities"
        indexes = [
            models.Index(fields=["plant_type", "capability"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_deleted", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["plant_type", "capability"],
                condition=models.Q(is_deleted=False),
                name="unique_active_plant_type_capability",
            ),
        ]

    def __str__(self):
        return f"{self.plant_type.code} - {self.capability.code}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.status == "Inactive" and self.pk:
            from common.models import Plant

            active_plants = Plant.objects.filter(
                plant_type=self.plant_type, status="Active", deleted=False
            ).exists()
            if active_plants:
                raise ValidationError(
                    "Cannot deactivate capability mapping. Active plants exist with this plant type."
                )


class Plant(BaseModule):
    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plant_code = models.CharField(max_length=50, unique=True, db_index=True)
    plant_name = models.CharField(max_length=255)
    plant_type = models.ForeignKey(
        PlantType,
        on_delete=models.PROTECT,
        related_name="plants",
        db_index=True,
        help_text="Plant type determines available capabilities",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(max_length=255)
    plant_head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plants_headed",
        db_index=True,
        help_text="Plant head user (must have Plant Head role)",
    )
    deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "plant"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["plant_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["city"]),
            models.Index(fields=["deleted", "status"]),
        ]

    def __str__(self):
        return f"{self.plant_code} - {self.plant_name}"


class SectionType(models.Model):
    """
    Section Type Master - Defines standardized section types used across ERP
    Used in department/section mapping and future workflow logic
    """

    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Section type name (e.g., Production, Quality, Maintenance)",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sectiontype_created",
        db_index=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sectiontype_updated",
        db_index=True,
    )
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "section_type"
        ordering = ["name"]
        verbose_name = "Section Type"
        verbose_name_plural = "Section Types"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_archived", "is_active"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(is_archived=False),
                name="unique_active_section_type_name",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Override save to prevent hard delete"""
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent hard delete - use archive instead"""
        raise ValueError("Hard delete not allowed. Use archive (soft delete) instead.")


class Department(models.Model):
    """
    Department Master - Defines departments within plants
    Used for organizational structure and workflow management
    """

    DEPARTMENT_TYPE_CHOICES = (
        ("PRODUCTION", "Production"),
        ("STORE", "Store"),
        ("QA", "Quality Assurance"),
        ("PURCHASE", "Purchase"),
        ("MAINTENANCE", "Maintenance"),
        ("FINANCE", "Finance"),
        ("ADMIN", "Administration"),
    )

    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department_code = models.CharField(
        max_length=50, unique=True, db_index=True, help_text="Unique department code"
    )
    department_name = models.CharField(max_length=255, db_index=True)
    department_type = models.CharField(
        max_length=20,
        choices=DEPARTMENT_TYPE_CHOICES,
        db_index=True,
        help_text="Type of department",
    )
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departments",
        db_index=True,
        help_text="Plant this department belongs to (optional)",
    )
    cost_center_code = models.CharField(
        max_length=50, blank=True, null=True, db_index=True
    )
    parent_department = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_departments",
        db_index=True,
        help_text="Parent department for hierarchical structure",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="department_created",
        db_index=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="department_updated",
        db_index=True,
    )

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.updated_at = None
        else:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        db_table = "department"
        ordering = ["department_code"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        permissions = [
            ("download_department_pdf_copy", "Can download department PDF"),
            ("download_department_excel_copy", "Can download department Excel"),
        ]
        indexes = [
            models.Index(fields=["department_code"]),
            models.Index(fields=["department_name"]),
            models.Index(fields=["department_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_archived", "status"]),
            models.Index(fields=["plant"]),
            models.Index(fields=["parent_department"]),
            models.Index(fields=["cost_center_code"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["plant", "is_archived", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["department_code"],
                condition=models.Q(is_archived=False),
                name="unique_active_department_code",
            ),
        ]

    def __str__(self):
        return f"{self.department_code} - {self.department_name}"

    def save(self, *args, **kwargs):
        """Override save to normalize department_code"""
        if self.department_code:
            self.department_code = self.department_code.strip().upper()
        if self.department_name:
            self.department_name = self.department_name.strip()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent hard delete - use archive instead"""
        raise ValueError("Hard delete not allowed. Use archive (soft delete) instead.")

class ItemCategory(models.Model):
    """
    Item Category Master - Classifies inventory items for Aluminum Extrusion ERP
    Controls allowed item types per category
    Used by Item Master, Inventory, Purchase & Reports
    """

    ITEM_TYPE_CHOICES = (
        ("RAW", "Raw Material"),
        ("CONSUMABLE", "Consumable"),
        ("SEMI", "Semi-Finished"),
        ("FG", "Finished Goods"),
        ("SPARE", "Spare Parts"),
        ("SCRAP", "Scrap"),
        ("TOOLING", "Tooling"),
    )

    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_code = models.CharField(
        max_length=50, unique=True, db_index=True, help_text="Unique category code"
    )
    category_name = models.CharField(max_length=255, db_index=True)
    allowed_item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        db_index=True,
        help_text="Allowed item type for this category",
    )
    description = models.TextField(
        blank=True, null=True, help_text="Category description"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="itemcategory_created",
        db_index=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="itemcategory_updated",
        db_index=True,
    )

    class Meta:
        db_table = "item_category"
        ordering = ["category_code"]
        verbose_name = "Item Category"
        verbose_name_plural = "Item Categories"
        indexes = [
            models.Index(fields=["category_code"]),
            models.Index(fields=["category_name"]),
            models.Index(fields=["allowed_item_type"]),
            # models.Index(fields=["is_active"]),
            models.Index(fields=["is_archived"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["allowed_item_type", "is_archived"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["category_code"],
                condition=models.Q(is_archived=False),
                name="unique_active_item_category_code",
            ),
        ]
        permissions = [
            ("download_item_category_pdf_copy", "Can download item category PDF"),
            ("download_item_category_excel_copy", "Can download item category Excel"),
        ]

    def __str__(self):
        return f"{self.category_code} - {self.category_name}"

    def save(self, *args, **kwargs):
        """Override save to normalize category_code"""
        if self.category_code:
            self.category_code = self.category_code.strip().upper()
        if self.category_name:
            self.category_name = self.category_name.strip()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent hard delete - use archive instead"""
        raise ValueError("Hard delete not allowed. Use archive (soft delete) instead.")


class UOM(BaseModel):
    class UOMType(models.TextChoices):
        WEIGHT = "WEIGHT", "Weight"
        LENGTH = "LENGTH", "Length"
        COUNT = "COUNT", "Count"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uom_name = models.CharField(max_length=50)
    uom_type = models.CharField(max_length=10, choices=UOMType.choices)
    decimal_allowed = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uom_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "uom"

    def __str__(self):
        return f"{self.uom_name}"


class YieldUnit(BaseModule):
    name = models.CharField(max_length=100, unique=True, null=True, blank=True)

    class Meta:
        db_table = "yield_unit"

    def __str__(self):
        return f"{self.name}"


class StoreType(BaseModule):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True, unique=True)

    class Meta:
        db_table = "store_type"

    def __str__(self):

        return f"{self.name}"


