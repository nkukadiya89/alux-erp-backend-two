from rest_framework import serializers
from .models import RecoveryStandardMaster

class RecoveryStandardMasterSerializers(serializers.ModelSerializer):
    class Meta:
        model = RecoveryStandardMaster
        fields= "__all__"