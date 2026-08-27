from rest_framework import serializers

from bloster.serializers import BlosterMasterSortSerializer
from common.serializers import BaseModelSerializer
from die.models import DiePress, DieTool
from die.serializers import DieToolSerializers
from workorder.sort_serializers import WorkOrderListSerializer

from .models import DieRequisition, DieRequisitionDetail


class PressNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiePress
        fields = ["id", "name"]


class DieToolSortSerializer(serializers.ModelSerializer):
    class Meta:
        model = DieTool
        fields = ["id", "tool_number"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret["eligible_bloster"] = (
            BlosterMasterSortSerializer(instance.eligible_bloster.all(), many=True).data
            if instance.eligible_bloster.exists()
            else []
        )
        return ret


class DieRequisitionDetailListSerializer(serializers.ModelSerializer):
    press = PressNestedSerializer()
    die_tool = DieToolSortSerializer(read_only=True)

    class Meta:
        model = DieRequisitionDetail
        fields = ["id", "press", "cavity", "die_tool"]


class DieRequisitionSortSerializer(serializers.ModelSerializer):
    die_requisition_detail = DieRequisitionDetailListSerializer(
        source="die_requisition", many=True
    )

    class Meta:
        model = DieRequisition
        fields = ["id", "die_requisition_detail"]


class DieRequisitionDetailSortSerializer(serializers.ModelSerializer):
    die_tool = serializers.CharField(source="die_tool.tool_number")
    die_number = serializers.CharField(source="die_tool.die.die_number")

    class Meta:
        model = DieRequisitionDetail
        fields = [
            "id",
            "die_tool",
            "die_number",
            "actual_qty_produced",
            "billets_used",
            "die_return_date",
            "die_condition_after",
            "remarks",
        ]


class DieRequisitionDetailCloseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = DieRequisitionDetail
        fields = [
            "id",
            "actual_qty_produced",
            "billets_used",
            "die_return_date",
            "die_condition_after",
            "remarks",
        ]


class DieRequisitionRejectSerializer(serializers.ModelSerializer):
    rejection_reason = serializers.CharField(required=True)

    class Meta:
        model = DieRequisition
        fields = [
            "rejection_reason",
        ]


class DieRequisitionDetailSerializer(BaseModelSerializer):
    die_tool = DieToolSerializers(read_only=True)
    requisition = serializers.PrimaryKeyRelatedField(
        queryset=DieRequisition.objects.all(), required=False, allow_null=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = DieRequisitionDetail
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "requisition",
            "die_tool",
            "die_tool",
            "profile_number",
            "press",
            "cavity",
            "location",
            "life_balance",
            "expected_output_kg",
            "approval_status",
            "actual_qty_produced",
            "billets_used",
            "die_return_date",
            "die_condition_after",
            "remarks",
        ]


class DieRequisitionDetailCreateSerializer(serializers.ModelSerializer):
    requisition = serializers.PrimaryKeyRelatedField(
        queryset=DieRequisition.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = DieRequisitionDetail
        fields = [
            "id",
            "die_tool",
            "profile_number",
            "press",
            "cavity",
            "requisition",
            "location",
            "life_balance",
            "expected_output_kg",
            "approval_status",
            "actual_qty_produced",
            "billets_used",
            "die_return_date",
            "die_condition_after",
            "remarks",
        ]


class DieRequisitionListSerializer(BaseModelSerializer):
    workorder_no = serializers.CharField(source="workorder_no.order_no", read_only=True)
    customer_name = serializers.CharField(
        source="workorder_no.bill_to.customer_name", read_only=True
    )
    customer_code = serializers.CharField(
        source="workorder_no.bill_to.code", read_only=True
    )
    planning_no = serializers.SerializerMethodField()
    planning_status = serializers.SerializerMethodField()
    planning_die_number = serializers.SerializerMethodField()
    die_requisition_items = DieRequisitionDetailSortSerializer(
        source="die_requisition", many=True, read_only=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = DieRequisition
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "requisition_no",
            "requisition_date",
            "workorder_no",
            "die_requisition_items",
            "customer_name",
            "customer_code",
            "planning_status",
            "planning_no",
            "planning_die_number",
            "priority",
            "status",
        ]

    def get_planning_no(self, obj):
        planning = obj.planning_die_requisition.first()
        return planning.planning_no if planning else None

    def get_planning_status(self, obj):
        planning = obj.planning_die_requisition.first()
        return planning.status if planning else None
    
    def get_planning_die_number(self, obj):
        planning = obj.planning_die_requisition.first()
        return planning.profile_no.die_number if planning else None


class DieRequisitionSerializer(BaseModelSerializer):
    workorder_details = WorkOrderListSerializer(source="workorder_no", read_only=True)
    die_requisition_details = DieRequisitionDetailSerializer(
        source="die_requisition", many=True, read_only=True
    )
    planning_details = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = DieRequisition
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "requisition_no",
            "requisition_date",
            "workorder_no",
            "workorder_details",
            "customer",
            "priority",
            "required_date",
            "status",
            "remarks",
            "die_requisition_details",
            "planning_details",
        ]

    def get_planning_details(self, obj):
        planning = obj.planning_die_requisition.first()

        return [
            {
                "id": planning.id,
                "planning_no": planning.planning_no,
                "status": planning.status,
                "plan_qty": planning.plan_qty,
                "plan_pcs": planning.plan_pcs,
                "die_profile": {
                    "id": planning.profile_no.id if planning.profile_no else None,
                    "die_number": planning.profile_no.die_number if planning.profile_no else None,
                    "die_type": planning.profile_no.die_type if planning.profile_no else None,
                }
            }
        ]


class DieRequisitionWriteSerializer(serializers.ModelSerializer):
    details = DieRequisitionDetailCreateSerializer(
        source="die_requisition", many=True, required=False
    )

    class Meta:
        model = DieRequisition
        fields = [
            "id",
            "requisition_date",
            "workorder_no",
            "customer",
            "priority",
            "required_date",
            "status",
            "remarks",
            "details",
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance and hasattr(instance, "die_requisition"):
            rep["details"] = DieRequisitionDetailCreateSerializer(
                instance.die_requisition.filter(deleted=False).order_by("id"), many=True
            ).data
        return rep

    def validate(self, data):
        if data.get("required_date") and data.get("requisition_date"):
            if data["required_date"] < data["requisition_date"]:
                raise serializers.ValidationError(
                    {"required_date": "Required date cannot be before requisition date"}
                )
        return data

    def create(self, validated_data):
        from utils.generate_number import generate_die_requisition_no

        details_data = validated_data.pop("details", [])
        request = self.context.get("request")
        created_by = request.user if request and hasattr(request, "user") else None

        validated_data["requisition_no"] = generate_die_requisition_no()

        requisition = DieRequisition.objects.create(**validated_data)

        for detail_data in details_data:
            detail_data = {
                k: v for k, v in detail_data.items() if k not in ("id", "requisition")
            }
            DieRequisitionDetail.objects.create(
                requisition=requisition, created_by=created_by, **detail_data
            )

        return requisition

    def update(self, instance, validated_data):
        details_data = validated_data.pop("details", None)
        request = self.context.get("request")
        updated_by = request.user if request and hasattr(request, "user") else None
        created_by = updated_by

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if details_data is not None:
            existing_details = {
                detail.id: detail
                for detail in instance.die_requisition.filter(deleted=False)
            }

            for detail_data in details_data:
                detail_id = detail_data.get("id")

                if detail_id:
                    if detail_id not in existing_details:
                        raise serializers.ValidationError(
                            {
                                "details": f"Die Requisition Detail with id {detail_id} does not belong to this requisition."
                            }
                        )
                    detail = existing_details[detail_id]
                    update_attrs = {
                        k: v
                        for k, v in detail_data.items()
                        if k not in ("id", "requisition")
                    }
                    for attr, value in update_attrs.items():
                        setattr(detail, attr, value)
                    if updated_by is not None:
                        detail.updated_by = updated_by
                    detail.save()
                else:
                    new_detail_data = {
                        k: v
                        for k, v in detail_data.items()
                        if k not in ("id", "requisition")
                    }
                    DieRequisitionDetail.objects.create(
                        requisition=instance, created_by=created_by, **new_detail_data
                    )

        return instance
