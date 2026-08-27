from common.serializers import BaseModelSerializer
from .models import VehicleType


class VehicleTypeSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = VehicleType
        fields = "__all__"
