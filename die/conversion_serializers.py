from django.db import transaction
from rest_framework import serializers

from common.serializers import BaseModelSerializer
from customer.models import Customer
from customer.serializers import CustomerListSerializer
from die.models import ConversionRate, ConversionRateItems, ConversionRateVersions
from die.sort_serializers import DieSortSerializers
from product.models import Alloy, Temper
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers


class ConversionRateVersionsSerializer(BaseModelSerializer):
    id = serializers.IntegerField(required=False)
    conversion_rate_items = serializers.PrimaryKeyRelatedField(
        queryset=ConversionRateItems.objects.all(), required=False, allow_null=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = ConversionRateVersions
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "conversion_rate_items",
            "date",
            "effective_from",
            "effective_to",
            "old_conversion",
            "new_conversion",
            "conversion",
            "difference",
            "percentage_change",
            "adjustment_type",
            "remarks",
        ]

        read_only_fields = [
            "date",
            "old_conversion",
            "difference",
            "percentage_change",
            "adjustment_type",
        ]


class ConversionRateItemsSerializer(BaseModelSerializer):
    id = serializers.IntegerField(required=False)
    versions = ConversionRateVersionsSerializer(
        many=True,
        required=False,
    )
    die = serializers.PrimaryKeyRelatedField(
        queryset=ConversionRateItems._meta.get_field("die").related_model.objects.all(),
        allow_null=True,
        required=False,
    )
    alloy = serializers.PrimaryKeyRelatedField(
        queryset=Alloy.objects.all(), allow_null=True, required=False
    )
    temper = serializers.PrimaryKeyRelatedField(
        queryset=Temper.objects.all(), allow_null=True, required=False
    )
    conversion_rate = serializers.PrimaryKeyRelatedField(
        queryset=ConversionRate.objects.all(), required=False, allow_null=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = ConversionRateItems
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "conversion_rate",
            "die",
            "alloy",
            "temper",
            "versions",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["die"] = DieSortSerializers(instance.die).data if instance.die else None
        ret["alloy"] = (
            AlloySortSerializers(instance.alloy).data if instance.alloy else None
        )
        ret["temper"] = (
            TemperSortSerializers(instance.temper).data if instance.temper else None
        )
        return ret


class ConversionRateSerializer(BaseModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), allow_null=True, required=False
    )
    items = ConversionRateItemsSerializer(
        many=True,
        required=False,
    )

    class Meta(BaseModelSerializer.Meta):
        model = ConversionRate
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "customer",
            "items",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["customer"] = (
            CustomerListSerializer(instance.customer).data
            if instance.customer
            else None
        )
        return ret

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        conversion_rate = ConversionRate.objects.create(**validated_data)
        user = self.context["request"].user

        for item_data in items_data:
            versions_data = item_data.pop("versions", [])
            item = ConversionRateItems.objects.create(
                conversion_rate=conversion_rate, **item_data, created_by=user
            )
            for version_data in versions_data:
                version_data.pop("conversion_rate_items", None)
                ConversionRateVersions.objects.create(
                    conversion_rate_items=item, **version_data, created_by=user
                )

        return conversion_rate

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        user = self.context["request"].user

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            existing_item_ids = set(
                instance.items.filter(deleted=False).values_list("id", flat=True)
            )
            incoming_item_ids = set()

            for item_data in items_data:
                versions_data = item_data.pop("versions", [])
                item_id = item_data.pop("id", None)

                if item_id:
                    incoming_item_ids.add(item_id)
                    item = ConversionRateItems.objects.filter(
                        id=item_id, conversion_rate=instance
                    ).first()
                    if item:
                        for attr, value in item_data.items():
                            setattr(item, attr, value)
                        item.save()
                else:
                    item = ConversionRateItems.objects.create(
                        conversion_rate=instance, **item_data, created_by=user
                    )
                    incoming_item_ids.add(item.id)

                existing_version_ids = set(
                    item.versions.filter(deleted=False).values_list("id", flat=True)
                )
                incoming_version_ids = set()

                for version_data in versions_data:
                    version_data.pop("conversion_rate_items", None)
                    version_id = version_data.pop("id", None)

                    if version_id:
                        incoming_version_ids.add(version_id)
                        ConversionRateVersions.objects.filter(
                            id=version_id, conversion_rate_items=item
                        ).update(**version_data)
                    else:
                        last_version = (
                            item.versions.filter(deleted=False).order_by("-id").first()
                        )

                        if (
                            last_version
                            and last_version.conversion
                            and version_data.get("conversion")
                        ):
                            old_val = float(last_version.conversion)
                            new_val = float(version_data["conversion"])
                            diff = round(new_val - old_val, 4)

                            version_data["old_conversion"] = old_val
                            version_data["new_conversion"] = new_val
                            version_data["difference"] = diff
                            version_data["percentage_change"] = (
                                round((diff / old_val) * 100, 2)
                                if old_val != 0
                                else None
                            )
                            version_data["adjustment_type"] = (
                                "Increase"
                                if diff > 0
                                else "Decrease" if diff < 0 else "No Change"
                            )

                        v = ConversionRateVersions.objects.create(
                            conversion_rate_items=item, **version_data, created_by=user
                        )
                        incoming_version_ids.add(v.id)

                versions_to_delete = existing_version_ids - incoming_version_ids
                if versions_to_delete:
                    ConversionRateVersions.objects.filter(
                        id__in=versions_to_delete
                    ).update(deleted=True)

            items_to_delete = existing_item_ids - incoming_item_ids
            if items_to_delete:
                ConversionRateItems.objects.filter(id__in=items_to_delete).update(
                    deleted=True
                )

        return instance


class ConversionRateListSerializer(BaseModelSerializer):
    customer = serializers.CharField(source="customer.customer_name")

    class Meta(BaseModelSerializer.Meta):
        model = ConversionRate
        fields = BaseModelSerializer.Meta.fields + ["id", "customer"]
