from django.utils.timezone import now
from rest_framework import serializers

from common.serializers import BaseModelSerializer

from .models import Transporter


class TransporterSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Transporter
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "party_name",
            "party_code",
            "opening_balance",
            "balance_type",
            "is_cash_amount",
            "address",
            "city",
            "pincode",
            "mobile_no_sms",
            "mobile_no",
            "phone_no",
            "email_id",
            "send_sms_type",
            "is_active",
        ]


class TransporterDropdownSerializer(serializers.ModelSerializer):
    """Lightweight for dropdown (id, party_name, party_code)."""

    class Meta:
        model = Transporter
        fields = ["id", "party_name", "party_code"]


class TransporterSortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transporter
        fields = [
            "id",
            "party_name",
        ]

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance = Transporter(**validated_data)
        instance.created_by = user
        instance.created_at = now()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance
