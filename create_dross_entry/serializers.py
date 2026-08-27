from rest_framework import serializers
from .models import DrossEntry, DrossDetail


class DrossDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrossDetail
        fields = "__all__"


# class DrossEntrySerializer(serializers.ModelSerializer):
#     dross_details = DrossDetailSerializer(
#         many=True,
#         read_only=True,
#         source="details"
#     )

#     class Meta:
#         model = DrossEntry
#         fields = "__all__"
        
class DrossEntrySerializer(serializers.ModelSerializer):
    dross_details = DrossDetailSerializer(many=True)

    class Meta:
        model = DrossEntry
        fields = "__all__"

    def create(self, validated_data):
        details = validated_data.pop("dross_details")
        shift = validated_data.pop("shift", None)
        
        if shift and not shift.is_active:
            raise serializers.ValidationError({"shift" : "Selected shift is inactive"})
    
        
        entry = DrossEntry.objects.create(**validated_data)
        
        if shift:
            entry.capture_shift_snapshot(shift)
            
        entry.save()

        for detail in details:
            DrossDetail.objects.create(
                dross_entry=entry,
                **detail
            )

        return entry