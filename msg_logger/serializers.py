# serializers.py
from rest_framework import serializers

from .models import LogActivity


class LogActivitySerializer(serializers.ModelSerializer):
    action_by_name = serializers.CharField(source="action_by.username", read_only=True)

    class Meta:
        model = LogActivity
        fields = [
            "id",
            "action",
            "action_by",
            "action_by_name",
            "module_name",
            "ip_address",
            "discription",
            "timestamp",
        ]
        read_only_fields = ["timestamp"]
