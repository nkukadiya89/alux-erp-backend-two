from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response

from .models import User


class CustomSlugRelatedField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            raise serializers.ValidationError(
                [f"Group '{data}' does not exist. Please provide valid group names."]
            )


class UserSerializer(serializers.ModelSerializer):
    groups = CustomSlugRelatedField(
        many=True, slug_field="name", queryset=Group.objects.all(), required=False
    )
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "groups",
            "status",
            "username",
            "phone",
            "profile_image",
            "deleted",
            "is_active",
            "keep_me_logged_in",
            "otp",
            "whatsapp_otp",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "last_login",
        ]
        read_only_fields = ["id"]

    def get_updated_by(self, obj):
        if obj.updated_by:
            return {
                "id": obj.updated_by.id,
                "first_name": obj.updated_by.first_name,
                "last_name": obj.updated_by.last_name,
            }
        return None

    def get_created_by(self, obj):
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "first_name": obj.created_by.first_name,
                "last_name": obj.created_by.last_name,
            }
        return None

    def create(self, validated_data):
        groups_data = validated_data.pop("groups", [])
        validated_data["created_at"] = timezone.now()
        user = User.objects.create(**validated_data)
        user.groups.set(groups_data)
        user.save()   
        return user

    def update(self, instance, validated_data):
        groups_data = validated_data.pop("groups", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if groups_data:
            instance.groups.set(groups_data)
        instance.updated_at = timezone.now()
        instance.save()
        return instance

    def delete(self, instance):
        if instance.deleted == 0:
            return Response(
                {"error": "User is already deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.deleted = 1
        instance.save()

        return Response(
            {"success": "User deleted successfully."}, status=status.HTTP_200_OK
        )


class UserArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = User
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                user = User.objects.get(id=deleted_id)
                user.deleted = 1
                user.save()

            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"success": False, "message": "User Does not Exists."}
                )

        return user


class UserRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = User
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                user = User.objects.get(id=deleted_id)
                user.deleted = 0
                user.save()

            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"success": False, "message": "User Does not Exists."}
                )

        return user
