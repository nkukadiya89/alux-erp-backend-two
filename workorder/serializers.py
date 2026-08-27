from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone
from rest_framework import serializers

from bundle_inward.models import BundleInward
from common.models import GstType, JobWorkType, PackingMode
from common.serializers import PackingModeSortSerializer, UserQuickSerializer
from customer.sort_serializers import CustomerBillToSerializer, CustomerShipToSerializer, CustomerSortListSerializer
from die.models import Die
from die.sort_serializers import DieSortSerializers, DieSortSerializers
from inquiry_salesorder.models import InquirySalesOrder
from product.models import Alloy, Temper
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from utils.calculate_weight_range import get_weight_range
from workorder.models import WorkOrder, WorkOrderDetail

class WorkOrderDetailListSerializer(serializers.ModelSerializer):
    die_detail = DieSortSerializers(source="die_profile", read_only=True)
    alloy = AlloySortSerializers(read_only=True)
    temper = TemperSortSerializers(read_only=True)

    class Meta:
        model = WorkOrderDetail
        fields = ["die_detail", "alloy", "temper", "length", "pieces", "net_weight"]


class WorkOrderDetailSerializers(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    weight_range = serializers.SerializerMethodField()
    workorder_no = serializers.CharField(source="workorder.order_no", read_only=True)
    workorder_id = serializers.IntegerField(source="workorder.id", read_only=True)

    class Meta:
        model = WorkOrderDetail
        fields = [
            "id",
            "salesorder_detail",
            "die_profile",
            "workorder_no",
            "workorder_id",
            "alloy",
            "temper",
            "surface_finish",
            "out_source",
            "cutting",
            "machining",
            "deburring",
            "cutting_price",
            "machining_price",
            "deburring_price",
            "anodising",
            "powder_coating",
            "pvdf",
            "anodising_price",
            "anodising_description",
            "powder_coating_price",
            "powder_coating_description",
            "pvdf_price",
            "pvdf_description",
            "laser_marking_description",
            "laser_marking_price",
            "length",
            "pieces",
            "net_weight",
            "max_weight",
            "min_weight",
            "nalco_rate",
            "packing_cost",
            "customer_reference_number",
            "conversion",
            "description",
            "modify_nalco_rate",
            "nalco_rate_change_reason",
            "status",
            "is_priority",
            "dispatched_weight",
            "packed_weight",
            "pending_weight",
            "packed_pieces",
            "dispatched_pieces",
            "pending_pieces",
            "weight_range",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "die_over_weight",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def get_weight_range(self, obj):
        return get_weight_range(
            obj.die_profile.wt_kg_p_mt, obj.length, obj.workorder.tolerance
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret["die_profile"] = (
            DieSortSerializers(instance.die_profile).data
            if instance.die_profile
            else None
        )
        ret["alloy"] = (
            AlloySortSerializers(instance.alloy).data if instance.alloy else None
        )
        ret["temper"] = (
            TemperSortSerializers(instance.temper).data if instance.temper else None
        )
        request = self.context.get("request")
        print_param = (
            request.query_params.get("print", "").lower() if request else "false"
        )
        if print_param in ["true", "1", "yes"]:
            ret["surface_finish"] = list(
                instance.surface_finish.values_list("name", flat=True)
            )
        else:
            ret["surface_finish"] = list(
                instance.surface_finish.values_list("id", flat=True)
            )

        for field in [
            "net_weight",
            "max_weight",
            "min_weight",
            "dispatched_weight",
            "packed_weight",
            "pending_weight",
        ]:
            if ret.get(field) is not None:
                ret[field] = f"{Decimal(str(ret[field])):.3f}"

        for field in [
            "nalco_rate",
            "conversion",
            "packing_cost",
            "cutting_price",
            "machining_price",
            "deburring_price",
            "anodising_price",
            "powder_coating_price",
            "pvdf_price",
            "laser_marking_price",
        ]:
            if ret.get(field) is not None:
                ret[field] = f"{Decimal(str(ret[field])):.2f}"

        return ret


class WorkOrderSerializers(serializers.ModelSerializer):
    salesorder = serializers.PrimaryKeyRelatedField(
        queryset=InquirySalesOrder.objects.all(), required=False, allow_null=True
    )
    packing_mode = serializers.PrimaryKeyRelatedField(
        queryset=PackingMode.objects.filter(deleted=False), many=True, required=False
    )
    packing_mode_details = PackingModeSortSerializer(
        source="packing_mode", many=True, read_only=True
    )
    work_order_details = serializers.ListField(required=False, allow_null=True)
    total_pieces = serializers.SerializerMethodField()
    total_weight = serializers.SerializerMethodField()
    total_bundle = serializers.SerializerMethodField()
    total_packed_weight = serializers.SerializerMethodField()
    total_pending_weight = serializers.SerializerMethodField()
    total_dispatched_weight = serializers.SerializerMethodField()

    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    approved_by_detail = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "bill_to",
            "ship_to",
            "reference_wo",
            "order_date",
            "order_type",
            "delivery_date",
            "purchase_order_no",
            "purchase_order_date",
            "project_name",
            "nalco_type",
            "salesorder",
            "terms_and_condition",
            "tolerance",
            "remarks",
            "status",
            "order_no",
            "planning_status",
            "packing_mode",
            "packing_mode_details",
            "packing_mode_other_reason",
            "po_copy",
            "reason_to_close",
            "wo_closing_doc",
            "approved_by",
            "approved_by_detail",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "work_order_details",
            "total_pieces",
            "total_weight",
            "total_bundle",
            "total_packed_weight",
            "total_pending_weight",
            "total_dispatched_weight",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def get_total_pieces(self, obj):
        """Calculate the total pieces from related WorkOrderDetail instances."""
        if hasattr(obj, "total_pieces_calc") and obj.total_pieces_calc is not None:
            return obj.total_pieces_calc
        return 0

    def get_total_bundle(self, obj):
        """Calculate the total_bundle from related WorkOrderDetail instances."""
        if hasattr(obj, "total_bundle_calc") and obj.total_bundle_calc is not None:
            return obj.total_bundle_calc
        return BundleInward.objects.filter(workorder=obj, deleted=False).count()

    def get_total_weight(self, obj):
        """Calculate the total weight from related WorkOrderDetail instances."""
        if hasattr(obj, "total_weight_calc") and obj.total_weight_calc is not None:
            return f"{Decimal(str(obj.total_weight_calc)):.3f}"
        return "0.000"

    def get_total_packed_weight(self, obj):
        """Calculate the total packed_weight from related WorkOrderDetail instances."""
        if (
            hasattr(obj, "total_packed_weight_calc")
            and obj.total_packed_weight_calc is not None
        ):
            return f"{Decimal(str(obj.total_packed_weight_calc)):.3f}"
        return "0.000"

    def get_total_pending_weight(self, obj):
        """Calculate the total pending_weight from related WorkOrderDetail instances."""
        if (
            hasattr(obj, "total_pending_weight_calc")
            and obj.total_pending_weight_calc is not None
        ):
            return f"{Decimal(str(obj.total_pending_weight_calc)):.3f}"
        return "0.000"

    def get_total_dispatched_weight(self, obj):
        """Calculate the total dispatched_weight from related WorkOrderDetail instances."""
        if (
            hasattr(obj, "total_dispatched_weight_calc")
            and obj.total_dispatched_weight_calc is not None
        ):
            return f"{Decimal(str(obj.total_dispatched_weight_calc)):.3f}"
        return "0.000"

    def get_approved_by_detail(self, obj):
        if obj.approved_by:
            return {
                "id": obj.approved_by.id,
                "first_name": obj.approved_by.first_name,
                "last_name": obj.approved_by.last_name,
            }
        return None

    def get_instance(self, model, id, error_message):
        try:
            return model.objects.get(id=id)
        except model.DoesNotExist:
            raise serializers.ValidationError(
                {"success": False, "message": error_message}
            )

    def create(self, validated_data):
        work_order_details_data = validated_data.pop("work_order_details", None)
        packing_mode_ids = validated_data.pop("packing_mode", [])
        validated_data["created_by"] = self.context["request"].user

        work_order_instance = WorkOrder.objects.create(**validated_data)

        if packing_mode_ids:
            work_order_instance.packing_mode.set(packing_mode_ids)

        if work_order_details_data is not None:
            for work_order_detail_data in work_order_details_data:

                jobwork_ids = work_order_detail_data.pop("surface_finish", [])
                work_order_detail_data.pop("surface_finish", None)
                jobwork_instances = []
                if isinstance(jobwork_ids, list) and jobwork_ids:
                    jobwork_instances = list(
                        JobWorkType.objects.filter(id__in=jobwork_ids)
                    )

                die_profile_id = work_order_detail_data.pop("die_profile", None)
                if die_profile_id is not None:
                    try:
                        die_instance = Die.objects.get(id=die_profile_id)
                        work_order_detail_data["die_profile"] = die_instance
                    except Die.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Die instance not found."}
                        )

                alloy_id = work_order_detail_data.pop("alloy", None)
                if alloy_id is not None:
                    try:
                        alloy_instance = Alloy.objects.get(id=alloy_id)
                        work_order_detail_data["alloy"] = alloy_instance
                    except Alloy.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Alloy instance not found."}
                        )

                temper_id = work_order_detail_data.pop("temper", None)
                if temper_id is not None:
                    try:
                        temper_instance = Temper.objects.get(id=temper_id)
                        work_order_detail_data["temper"] = temper_instance
                    except Temper.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Temper instance not found."}
                        )

                net_weight = Decimal(work_order_detail_data.get("net_weight", 0) or 0)
                dispatched_weight = Decimal(
                    work_order_detail_data.get("dispatched_weight", 0) or 0
                )
                packed_weight = Decimal(
                    work_order_detail_data.get("packed_weight", 0) or 0
                )
                pieces = int(work_order_detail_data.get("pieces", 0) or 0)
                dispatched_pieces = int(
                    work_order_detail_data.get("dispatched_pieces", 0) or 0
                )
                packed_pieces = int(work_order_detail_data.get("packed_pieces", 0) or 0)

                work_order_detail_data["die_over_weight"] = bool(
                    work_order_detail_data.get("die_over_weight", False)
                )

                work_order_detail_data["pending_weight"] = (
                    net_weight - dispatched_weight - packed_weight
                )
                work_order_detail_data["pending_pieces"] = (
                    pieces - dispatched_pieces - packed_pieces
                )

                work_order_detail_data["workorder"] = work_order_instance
                work_order_detail_data["created_by"] = self.context["request"].user
                work_order_detail_data["created_at"] = timezone.now()

                work_order_detail_instance = WorkOrderDetail.objects.create(
                    **work_order_detail_data
                )

                if jobwork_instances:
                    work_order_detail_instance.surface_finish.set(jobwork_instances)

                try:
                    from workorder.process_tracking import sync_jobwork_stages_for_detail

                    sync_jobwork_stages_for_detail(
                        work_order_detail_instance,
                        user=self.context["request"].user,
                    )
                except Exception:
                    pass

        return work_order_instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        packing_mode_ids = validated_data.pop("packing_mode", None)

        instance.bill_to = validated_data.get("bill_to", instance.bill_to)
        instance.ship_to = validated_data.get("ship_to", instance.ship_to)
        instance.delivery_date = validated_data.get(
            "delivery_date", instance.delivery_date
        )
        instance.purchase_order_no = validated_data.get(
            "purchase_order_no", instance.purchase_order_no
        )
        instance.purchase_order_date = validated_data.get(
            "purchase_order_date", instance.purchase_order_date
        )
        instance.project_name = validated_data.get(
            "project_name", instance.project_name
        )
        instance.nalco_type = validated_data.get("nalco_type", instance.nalco_type)
        instance.tolerance = validated_data.get("tolerance", instance.tolerance)
        instance.remarks = validated_data.get("remarks", instance.remarks)
        instance.packing_mode_other_reason = validated_data.get(
            "packing_mode_other_reason", instance.packing_mode_other_reason
        )
        instance.status = validated_data.get("status", instance.status)
        instance.order_no = validated_data.get("order_no", instance.order_no)
        instance.updated_by = request.user
        instance.updated_at = timezone.now()

        if packing_mode_ids is not None:
            instance.packing_mode.set(packing_mode_ids)

        work_order_details_data = validated_data.pop("work_order_details", None)
        work_order_details_instances = []
        new_work_order_details_instances = []

        skipped_updates = []

        if work_order_details_data is not None:
            work_order_details_ids = []

            for work_order_detail_data in work_order_details_data:
                work_order_detail_id = work_order_detail_data.get("id")
                work_order_details_ids.append(work_order_detail_id)
                workorder_detail_id = work_order_detail_data.get("id")
                new_work_order_detail_instance = None

                if workorder_detail_id:
                    try:
                        workorder_details_instance = WorkOrderDetail.objects.get(
                            id=workorder_detail_id
                        )
                    except WorkOrderDetail.DoesNotExist:
                        raise serializers.ValidationError(
                            {
                                "success": False,
                                "message": "Workorder Details not Found.",
                            }
                        )

                    current_status = workorder_details_instance.status

                    if current_status != "Pending":
                        if "die_over_weight" in work_order_detail_data:
                            workorder_details_instance.die_over_weight = (
                                work_order_detail_data.get("die_over_weight", False)
                            )
                            workorder_details_instance.updated_by = request.user
                            workorder_details_instance.updated_at = timezone.now()
                            workorder_details_instance.save()
                            work_order_details_instances.append(
                                workorder_details_instance
                            )

                        restricted_fields = [
                            k
                            for k in work_order_detail_data.keys()
                            if k not in ["id", "die_over_weight"]
                        ]
                        if restricted_fields:
                            die_number = (
                                workorder_details_instance.die_profile.die_number
                                if workorder_details_instance.die_profile
                                else "N/A"
                            )
                            length = workorder_details_instance.length or "N/A"
                            skipped_updates.append(
                                f"WorkOrderDetail with Profile Number '{die_number} / {length}mm' is in '{current_status}' status. Only 'Allow Access Profile Weight' field can be updated.",
                            )

                        continue

                    die_profile_id = work_order_detail_data.pop("die_profile", None)
                    alloy_id = work_order_detail_data.pop("alloy", None)
                    temper_id = work_order_detail_data.pop("temper", None)

                    if die_profile_id is not None:
                        try:
                            workorder_details_instance.die_profile = Die.objects.get(
                                id=die_profile_id
                            )
                        except Die.DoesNotExist:
                            raise serializers.ValidationError(
                                {"success": False, "message": "Die instance not found."}
                            )

                    if alloy_id is not None:
                        try:
                            workorder_details_instance.alloy = Alloy.objects.get(
                                id=alloy_id
                            )
                        except Alloy.DoesNotExist:
                            raise serializers.ValidationError(
                                {
                                    "success": False,
                                    "message": "Alloy instance not found.",
                                }
                            )

                    if temper_id is not None:
                        try:
                            workorder_details_instance.temper = Temper.objects.get(
                                id=temper_id
                            )
                        except Temper.DoesNotExist:
                            raise serializers.ValidationError(
                                {
                                    "success": False,
                                    "message": "Temper instance not found.",
                                }
                            )

                    jobwork_types_data = work_order_detail_data.get(
                        "surface_finish", []
                    )
                    if isinstance(jobwork_types_data, list):
                        jobwork_type_instances = JobWorkType.objects.filter(
                            id__in=jobwork_types_data
                        )
                        workorder_details_instance.surface_finish.set(
                            jobwork_type_instances
                        )
                    else:
                        workorder_details_instance.surface_finish.clear()

                    workorder_details_instance.out_source = work_order_detail_data.get(
                        "out_source"
                    )
                    workorder_details_instance.cutting = work_order_detail_data.get(
                        "cutting"
                    )
                    workorder_details_instance.machining = work_order_detail_data.get(
                        "machining"
                    )
                    workorder_details_instance.deburring = work_order_detail_data.get(
                        "deburring"
                    )
                    workorder_details_instance.cutting_price = (
                        work_order_detail_data.get("cutting_price")
                    )
                    workorder_details_instance.machining_price = (
                        work_order_detail_data.get("machining_price")
                    )
                    workorder_details_instance.deburring_price = (
                        work_order_detail_data.get("deburring_price")
                    )
                    workorder_details_instance.anodising = work_order_detail_data.get(
                        "anodising"
                    )
                    workorder_details_instance.powder_coating = (
                        work_order_detail_data.get("powder_coating")
                    )
                    workorder_details_instance.pvdf = work_order_detail_data.get("pvdf")
                    workorder_details_instance.anodising_description = (
                        work_order_detail_data.get("anodising_description")
                    )
                    workorder_details_instance.anodising_price = (
                        work_order_detail_data.get("anodising_price")
                    )
                    workorder_details_instance.powder_coating_description = (
                        work_order_detail_data.get("powder_coating_description")
                    )
                    workorder_details_instance.powder_coating_price = (
                        work_order_detail_data.get("powder_coating_price")
                    )
                    workorder_details_instance.pvdf_description = (
                        work_order_detail_data.get("pvdf_description")
                    )
                    workorder_details_instance.pvdf_price = work_order_detail_data.get(
                        "pvdf_price"
                    )
                    workorder_details_instance.laser_marking_description = (
                        work_order_detail_data.get("laser_marking_description")
                    )
                    workorder_details_instance.laser_marking_price = (
                        work_order_detail_data.get("laser_marking_price")
                    )
                    workorder_details_instance.length = work_order_detail_data.get(
                        "length"
                    )
                    workorder_details_instance.pieces = work_order_detail_data.get(
                        "pieces"
                    )
                    workorder_details_instance.net_weight = work_order_detail_data.get(
                        "net_weight"
                    )
                    workorder_details_instance.max_weight = work_order_detail_data.get(
                        "max_weight"
                    )
                    workorder_details_instance.min_weight = work_order_detail_data.get(
                        "min_weight"
                    )
                    workorder_details_instance.nalco_rate = work_order_detail_data.get(
                        "nalco_rate"
                    )
                    workorder_details_instance.packing_cost = (
                        work_order_detail_data.get("packing_cost")
                    )
                    workorder_details_instance.conversion = work_order_detail_data.get(
                        "conversion"
                    )
                    workorder_details_instance.customer_reference_number = (
                        work_order_detail_data.get("customer_reference_number")
                    )
                    workorder_details_instance.description = work_order_detail_data.get(
                        "description"
                    )
                    workorder_details_instance.modify_nalco_rate = (
                        work_order_detail_data.get("modify_nalco_rate")
                    )
                    workorder_details_instance.nalco_rate_change_reason = (
                        work_order_detail_data.get("nalco_rate_change_reason")
                    )
                    workorder_details_instance.is_priority = work_order_detail_data.get(
                        "is_priority", False
                    )
                    workorder_details_instance.die_over_weight = (
                        work_order_detail_data.get("die_over_weight", False)
                    )

                    net_weight = Decimal(workorder_details_instance.net_weight or 0)
                    dispatched_weight = Decimal(
                        workorder_details_instance.dispatched_weight or 0
                    )
                    packed_weight = Decimal(
                        workorder_details_instance.packed_weight or 0
                    )
                    pieces = int(workorder_details_instance.pieces or 0)
                    dispatched_pieces = int(
                        workorder_details_instance.dispatched_pieces or 0
                    )
                    packed_pieces = int(workorder_details_instance.packed_pieces or 0)

                    workorder_details_instance.pending_weight = (
                        net_weight - dispatched_weight - packed_weight
                    )
                    workorder_details_instance.pending_pieces = (
                        pieces - dispatched_pieces - packed_pieces
                    )
                    workorder_details_instance.updated_by = request.user
                    workorder_details_instance.updated_at = timezone.now()

                    work_order_details_instances.append(workorder_details_instance)
                    workorder_details_instance.save()

                    try:
                        from workorder.process_tracking import (
                            sync_jobwork_stages_for_detail,
                        )

                        sync_jobwork_stages_for_detail(
                            workorder_details_instance,
                            user=getattr(request, "user", None),
                        )
                    except Exception:
                        pass

                else:
                    new_workorder_data = {
                        "workorder": instance,
                        "out_source": work_order_detail_data.get("out_source", False),
                        "cutting": work_order_detail_data.get("cutting"),
                        "machining": work_order_detail_data.get("machining"),
                        "deburring": work_order_detail_data.get("deburring"),
                        "cutting_price": work_order_detail_data.get("cutting_price"),
                        "machining_price": work_order_detail_data.get(
                            "machining_price"
                        ),
                        "deburring_price": work_order_detail_data.get(
                            "deburring_price"
                        ),
                        "anodising": work_order_detail_data.get("anodising"),
                        "powder_coating": work_order_detail_data.get("powder_coating"),
                        "pvdf": work_order_detail_data.get("pvdf"),
                        "anodising_description": work_order_detail_data.get(
                            "anodising_description"
                        ),
                        "anodising_price": work_order_detail_data.get(
                            "anodising_price"
                        ),
                        "powder_coating_description": work_order_detail_data.get(
                            "powder_coating_description"
                        ),
                        "powder_coating_price": work_order_detail_data.get(
                            "powder_coating_price"
                        ),
                        "pvdf_description": work_order_detail_data.get(
                            "pvdf_description"
                        ),
                        "pvdf_price": work_order_detail_data.get("pvdf_price"),
                        "laser_marking_description": work_order_detail_data.get(
                            "laser_marking_description"
                        ),
                        "laser_marking_price": work_order_detail_data.get(
                            "laser_marking_price"
                        ),
                        "length": work_order_detail_data.get("length"),
                        "pieces": work_order_detail_data.get("pieces"),
                        "net_weight": work_order_detail_data.get("net_weight"),
                        "max_weight": work_order_detail_data.get("max_weight"),
                        "min_weight": work_order_detail_data.get("min_weight"),
                        "nalco_rate": work_order_detail_data.get("nalco_rate"),
                        "packing_cost": work_order_detail_data.get("packing_cost"),
                        "conversion": work_order_detail_data.get("conversion"),
                        "customer_reference_number": work_order_detail_data.get(
                            "customer_reference_number"
                        ),
                        "description": work_order_detail_data.get("description"),
                        "modify_nalco_rate": work_order_detail_data.get(
                            "modify_nalco_rate"
                        ),
                        "nalco_rate_change_reason": work_order_detail_data.get(
                            "nalco_rate_change_reason"
                        ),
                        "is_priority": work_order_detail_data.get("is_priority", False),
                        "die_over_weight": work_order_detail_data.get(
                            "die_over_weight", False
                        ),
                        "updated_by": request.user,
                        "updated_at": timezone.now(),
                    }

                    die_profile_id = work_order_detail_data.get("die_profile")
                    alloy_id = work_order_detail_data.get("alloy")
                    temper_id = work_order_detail_data.get("temper")

                    if die_profile_id is not None:
                        new_workorder_data["die_profile"] = self.get_instance(
                            Die, die_profile_id, "Die Not Found"
                        )
                    if alloy_id is not None:
                        new_workorder_data["alloy"] = self.get_instance(
                            Alloy, alloy_id, "Alloy Not Found"
                        )
                    if temper_id is not None:
                        new_workorder_data["temper"] = self.get_instance(
                            Temper, temper_id, "Temper Not Found"
                        )

                    net_weight = Decimal(new_workorder_data.get("net_weight", 0) or 0)
                    dispatched_weight = Decimal(0)
                    packed_weight = Decimal(0)
                    pieces = int(new_workorder_data.get("pieces", 0) or 0)
                    dispatched_pieces = 0
                    packed_pieces = 0

                    new_workorder_data["pending_weight"] = (
                        net_weight - dispatched_weight - packed_weight
                    )
                    new_workorder_data["pending_pieces"] = (
                        pieces - dispatched_pieces - packed_pieces
                    )

                    new_work_order_detail_instance = WorkOrderDetail.objects.create(
                        **new_workorder_data
                    )

                    jobwork_types_data = work_order_detail_data.get(
                        "surface_finish", []
                    )
                    if isinstance(jobwork_types_data, list):
                        jobwork_type_instances = JobWorkType.objects.filter(
                            id__in=jobwork_types_data
                        )
                        new_work_order_detail_instance.surface_finish.set(
                            jobwork_type_instances
                        )

                    try:
                        from workorder.process_tracking import (
                            sync_jobwork_stages_for_detail,
                        )

                        sync_jobwork_stages_for_detail(
                            new_work_order_detail_instance,
                            user=getattr(request, "user", None),
                        )
                    except Exception:
                        pass

                    new_work_order_details_instances.append(
                        new_work_order_detail_instance
                    )
                    work_order_details_ids.append(new_work_order_detail_instance.id)

            if len(work_order_details_ids) > 0:
                if new_work_order_detail_instance:
                    workorder_detail_ids = [
                        workorder_detail.id
                        for workorder_detail in new_work_order_details_instances
                    ]
                    WorkOrderDetail.objects.filter(workorder=instance).exclude(
                        id__in=work_order_details_ids
                    ).exclude(id__in=workorder_detail_ids).update(deleted=True)
                else:
                    WorkOrderDetail.objects.filter(workorder=instance).exclude(
                        id__in=work_order_details_ids
                    ).update(deleted=True)
        instance.save()
        self.context["skipped_updates"] = skipped_updates

        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "bill_to" in ret:
            ret["bill_to"] = CustomerBillToSerializer(instance.bill_to).data

        if "ship_to" in ret:
            ret["ship_to"] = CustomerShipToSerializer(instance.ship_to).data

        ret["packing_mode"] = list(instance.packing_mode.values_list("id", flat=True))

        work_order_details = []
        total_basic_summary = Decimal("0")
        gst_amount_summary = Decimal("0")
        total_amount_summary = Decimal("0")

        try:
            queryset = instance.workorder_detail_workorder.filter(deleted=False).order_by("id")

            gst_percent = Decimal("0")
            if instance.bill_to and hasattr(instance.bill_to, "applicable_gst"):
                applicable_gst = instance.bill_to.applicable_gst or ""
                gst_names = []
                if "sgst_cgst" in applicable_gst.lower():
                    gst_names = ["sgst", "cgst"]
                else:
                    gst_names = [applicable_gst.lower()]

                gst_objects = GstType.objects.filter(name__in=gst_names)
                gst_percent = sum(
                    (gst.percentage or Decimal("0")) for gst in gst_objects
                )

            for detail in queryset:
                data = WorkOrderDetailSerializers(detail, context=self.context).data

                conversion = detail.conversion or 0
                nalco_rate = detail.nalco_rate or 0
                net_weight = detail.net_weight or 0

                if detail.workorder.nalco_type == "Variable":
                    data["price_per_kg"] = (
                        f"Variable + {float(f'{Decimal(str(conversion)):.2f}')}"
                    )
                    total_basic = conversion * net_weight
                    total_basic = (Decimal(conversion) * Decimal(net_weight)).quantize(
                        Decimal("0.00"), rounding=ROUND_HALF_UP
                    )
                else:
                    data["price_per_kg"] = float(
                        f"{Decimal(str(nalco_rate + conversion)):.2f}"
                    )
                    total_basic = (nalco_rate + conversion) * net_weight
                    total_basic = (Decimal(conversion) * Decimal(net_weight)).quantize(
                        Decimal("0.00"), rounding=ROUND_HALF_UP
                    )

                cutting_price = Decimal(detail.cutting_price or 0) * net_weight
                machining_price = Decimal(detail.machining_price or 0) * net_weight
                deburring_price = Decimal(detail.deburring_price or 0) * net_weight
                anodising_price = Decimal(detail.anodising_price or 0) * net_weight
                powder_coating_price = (
                    Decimal(detail.powder_coating_price or 0) * net_weight
                )
                pvdf_price = Decimal(detail.pvdf_price or 0) * net_weight
                laser_marking_price = (
                    Decimal(detail.laser_marking_price or 0) * net_weight
                )

                additional_prices_total = (
                    cutting_price
                    + machining_price
                    + deburring_price
                    + anodising_price
                    + powder_coating_price
                    + pvdf_price
                    + laser_marking_price
                )

                total_basic += additional_prices_total
                data["total_basic_amount"] = format(float(total_basic), ".2f")
                data["additional_prices_total"] = format(
                    float(additional_prices_total), ".2f"
                )
                total_basic_summary += total_basic

                gst_amount = (Decimal(total_basic) * gst_percent) / Decimal("100")
                total_amount = Decimal(total_basic) + gst_amount

                data["gst_percent"] = float(f"{Decimal(gst_percent):.2f}")
                data["gst_amount"] = float(f"{Decimal(gst_amount):.2f}")
                data["total_amount"] = float(f"{Decimal(total_amount):.2f}")

                gst_amount_summary += gst_amount
                total_amount_summary += total_amount

                work_order_details.append(data)

        except WorkOrderDetail.DoesNotExist:
            work_order_details = [
                {
                    "id": None,
                    "die_profile": None,
                    "alloy": None,
                    "temper": None,
                    "surface_finish": None,
                    "out_source": False,
                    "cutting": None,
                    "machining": None,
                    "deburring": None,
                    "cutting_price": None,
                    "machining_price": None,
                    "deburring_price": None,
                    "anodising": None,
                    "powder_coating": None,
                    "pvdf": None,
                    "anodising_description": None,
                    "anodising_price": None,
                    "powder_coating_description": None,
                    "powder_coating_price": None,
                    "pvdf_description": None,
                    "pvdf_price": None,
                    "laser_marking_description": None,
                    "laser_marking_price": None,
                    "length": None,
                    "pieces": None,
                    "net_weight": None,
                    "max_weight": None,
                    "min_weight": None,
                    "nalco_rate": None,
                    "packing_cost": None,
                    "customer_reference_number": None,
                    "conversion": None,
                    "description": None,
                    "modify_nalco_rate": None,
                    "nalco_rate_change_reason": None,
                    "status": None,
                    "packed_weight": None,
                    "dispatched_weight": None,
                    "pending_weight": None,
                    "packed_pieces": None,
                    "dispatched_pieces": None,
                    "pending_pieces": None,
                    "price_per_kg": None,
                    "total_basic_amount": None,
                    "gst_amount": None,
                    "total_amount": None,
                    "gst_percent": None,
                }
            ]

        ret["work_order_details"] = work_order_details
        ret["total_basic_amount"] = format(float(total_basic_summary), ".2f")
        ret["total_gst_amount"] = format(float(gst_amount_summary), ".2f")
        ret["total_amount"] = format(float(total_amount_summary), ".2f")

        return ret


class WorkOrderSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "bill_to",
            "ship_to",
            "order_date",
            "order_no",
            "delivery_date",
        ]
