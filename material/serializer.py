from django.utils.timezone import now

from common.serializers import BaseModelSerializer

from .models import Material


class MaterialSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Material
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "material_name",
        ]

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance = Material(**validated_data)
        instance.created_by = user
        instance.created_at = now()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for field in [
            "material_name",
            "deleted",
        ]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance
