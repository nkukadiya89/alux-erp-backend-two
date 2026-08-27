from django.contrib.auth.models import Permission
from rest_framework import serializers

from email_utils.base_mail import new_user_registeration
from user.models import ContentTypeModel, CustomGroup, User, UserGroupsModel


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        validated_data["username"] = validated_data["email"]
        user = User.objects.create_user(**validated_data)
        user.is_active = True
        user.save()
        new_user_registeration(user)
        return user


class CustomGroupSerializers(serializers.ModelSerializer):
    sequence = serializers.IntegerField(source="customgroup.sequence", read_only=True)
    name = serializers.CharField()
    permissions = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()

    class Meta:
        model = CustomGroup
        fields = [
            "id",
            "name",
            "users",
            "sequence",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted",
            "permissions",
        ]

    def get_users(self, obj):
        user_group_entries = UserGroupsModel.objects.filter(group_id=obj.id)
        user_names = user_group_entries.select_related("user").values_list(
            "user__first_name", flat=True
        )
        return list(user_names)

    def get_updated_by(self, obj):
        if obj.updated_by:
            return {
                "id": obj.updated_by.id,
                "first_name": obj.updated_by.first_name,
                "last_name": obj.updated_by.last_name,
            }
        return None

    def get_created_by(self, obj):
        print("obj type:", type(obj))  # Ensure this is CustomGroup
        if hasattr(obj, "created_by") and obj.created_by:
            return {
                "id": obj.created_by.id,
                "first_name": obj.created_by.first_name,
                "last_name": obj.created_by.last_name,
            }
        return None

    # def get_permissions(self, obj):
    #     # Return a list of assigned permissions for the group
    #     return obj.permissions.values("id", "codename", "name")

    def get_permissions(self, obj):
        # Get all permissions for the group
        permissions = obj.permissions.values("id", "codename", "name")

        # Define the order of permission types
        permission_order = {"add": 0, "change": 1, "delete": 2, "view": 3}

        # Sort permissions based on the action type
        sorted_permissions = sorted(
            permissions,
            key=lambda perm: permission_order.get(
                perm["codename"].split("_")[0], 4
            ),  # Default to 4 if not found
        )

        return sorted_permissions

    def create(self, validated_data):
        # Check for duplicate group name
        if CustomGroup.objects.filter(name=validated_data["name"]).exists():
            raise serializers.ValidationError(
                {"name": "A group with this name already exists."}
            )

        return super().create(validated_data)


class ContentTypeSerializers(serializers.ModelSerializer):
    permission_on = serializers.CharField(source="model")

    class Meta:
        model = ContentTypeModel
        fields = ["id", "permission_on"]


class PermissionSerializers(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = [
            "id",
            "name",
            "codename",
            "content_type",
        ]


class GroupArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = CustomGroup
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                group = CustomGroup.objects.get(id=deleted_id)
                group.deleted = 1
                group.save()

            except CustomGroup.DoesNotExist:
                raise serializers.ValidationError(
                    {"success": False, "message": "Group Does not Exists."}
                )

        return group


class GroupRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = CustomGroup
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                group = CustomGroup.objects.get(id=deleted_id)
                group.deleted = 0
                group.save()

            except CustomGroup.DoesNotExist:
                raise serializers.ValidationError(
                    {"success": False, "message": "Group Does not Exists."}
                )

        return group


class UserQuickSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "full_name"]

    def get_full_name(self, obj):
        stored = (obj.full_name or "").strip()
        if stored:
            return stored
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip()
