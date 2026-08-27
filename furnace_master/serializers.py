from common.serializers import BaseModelSerializer
from .models import FurnaceMaster


class FurnaceMasterSerializer(BaseModelSerializer):
    class Meta:
        model = FurnaceMaster
        fields = [
            "id",
            "code",
            "name",
            "type",
            "capacity_kg",
            "min_temp_celsius",
            "max_temp_celsius",
            "fuel_type",
            "remarks",
            "status",
        ]