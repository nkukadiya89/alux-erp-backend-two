from utils.generate_number import generate_aging_cycle_no
from common.serializers import BaseModelSerializer
from ageing_cycle.models import AgingCycle
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers

class AgingCycleSerializer(BaseModelSerializer):
    class Meta:
        model = AgingCycle
        fields = "__all__"

    def create(self, validated_data):
        validated_data["cycle_code"] = generate_aging_cycle_no()
        aging_cycle = AgingCycle(**validated_data)
        aging_cycle.save()
        return aging_cycle


class AgingCycleListSerializer(BaseModelSerializer):
    alloy = AlloySortSerializers(read_only=True)    
    temper = TemperSortSerializers(read_only=True)
    class Meta:
        model = AgingCycle
        fields = [
            "id",
            "cycle_name",
            "cycle_code",
            "alloy",
            "temper",
            "zone1_temp",
            "zone2_temp",
            "zone3_temp",
            "zone4_temp",
            "soaking_time",
            "cooling_type",
            "remarks",
        ]