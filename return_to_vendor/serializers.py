from rest_framework import serializers
from .models import ReturnToVendor


class ReturnToVendorSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReturnToVendor
        fields = "__all__"
        