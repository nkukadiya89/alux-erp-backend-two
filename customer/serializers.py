from django.db import transaction
from rest_framework import serializers
from common.serializers import BaseModelListSerializer, BaseModelSerializer
from customer.models import BankingDetails, Customer, CustomerType
from die.models import Die, DieGroup
from user.models import User
from user.serializers import UserQuickSerializer


class CustomerTypeSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = CustomerType
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "name",
        ]

class CustomerTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerType
        fields = ["id", "name"]

class BankingDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankingDetails
        fields = [
            "id",
            "bank_name",
            "bank_account_number",
            "bank_ifsc_code",
            "bank_branch_address",
            "beneficiary_swift_code",
            "bank_ad_code",
        ]


class CustomerDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Customer dropdown API - active and non-archived only"""

    class Meta:
        model = Customer
        fields = ["id", "customer_name", "person_name"]


class QuickCustomerSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Customer
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "customer_name",
            "person_name",
            "email",
            "phone_number",
            "applicable_gst",
            "designation",
        ]


class CustomerSerializer(BaseModelSerializer):
    banking_details = BankingDetailSerializer(many=True, required=False)
    die_numbers = serializers.SerializerMethodField()
    due_days = serializers.IntegerField(allow_null=True, required=False)
    delivery_days = serializers.IntegerField(allow_null=True, required=False)
    credit_limit = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True, required=False
    )

    class Meta(BaseModelSerializer.Meta):
        model = Customer
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "business_type",
            "gstin_number",
            "gst_type",
            "pan_number",
            "trade_name",
            "code",
            "designation",
            "fax_number",
            "website",
            "beneficiary_agent_code",
            "import_export_code",
            "customer_name",
            "person_name",
            "email",
            "phone_number",
            "customer_type",
            "sales_executive",
            "sales_executive_assistant",
            "delivery_days",
            "udyam_no",
            "applicable_gst",
            "office_address_shop",
            "office_address_area",
            "office_address_landmark",
            "office_address_pin_code",
            "office_address_city",
            "office_address_state",
            "office_address_country",
            "factory_address_shop",
            "factory_address_area",
            "factory_address_landmark",
            "factory_address_pin_code",
            "factory_address_city",
            "factory_address_state",
            "factory_address_country",
            "banking_details",
            "is_company_visible_on_documents",
            "credit_limit",
            "due_days",
            "licence_no",
            "note",
            "customer_balance",
            "amount",
            "company_type",
            "die_numbers",
        ]

    def get_die_numbers(self, obj):

        customer_name = (obj.customer_name or "").strip().lower()
        if not customer_name:
            return []

        matching_group = DieGroup.objects.filter(name__iexact=customer_name).first()
        if not matching_group:
            return []

        die_qs = Die.objects.filter(die_group=matching_group).values_list(
            "die_number", flat=True
        )
        return list(die_qs)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["amount"] = instance.amount if instance.amount is not None else None
        if instance.customer_type:
            ret["customer_type"] = CustomerTypeSerializer(instance.customer_type).data
        else:
            ret["customer_type"] = None

        if instance.sales_executive:
            ret["sales_executive"] = {
                "id": instance.sales_executive.id,
                "first_name": instance.sales_executive.first_name,
                "last_name": instance.sales_executive.last_name,
            }
        else:
            ret["sales_executive"] = None

        if instance.sales_executive_assistant:
            ret["sales_executive_assistant"] = {
                "id": instance.sales_executive_assistant.id,
                "first_name": instance.sales_executive_assistant.first_name,
                "last_name": instance.sales_executive_assistant.last_name,
            }
        else:
            ret["sales_executive_assistant"] = None
        ret["banking_details"] = BankingDetailSerializer(
            instance.banking_details.filter(deleted=0), many=True
        ).data

        return ret

    @transaction.atomic
    def create(self, validated_data):
        banking_details_data = validated_data.pop("banking_details", [])
        customer = Customer.objects.create(**validated_data)
        for bank in banking_details_data:
            BankingDetails.objects.create(customer=customer, **bank)
        return customer

    @transaction.atomic
    def update(self, instance, validated_data):
        banking_details_data = validated_data.pop("banking_details", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        BankingDetails.objects.filter(customer=instance).delete()
        for bank in banking_details_data:
            BankingDetails.objects.create(customer=instance, **bank)
        return instance


class CustomerInfoSerializer(BaseModelListSerializer):
    customer_type = serializers.CharField(source="customer_type.name", read_only=True)
    sales_executive = serializers.CharField(source="sales_executive.first_name", read_only=True)
    sales_executive_assistant = serializers.CharField(source="sales_executive_assistant.first_name", read_only=True)

    class Meta(BaseModelListSerializer.Meta):
        model = Customer
        fields = BaseModelListSerializer.Meta.fields + [
            "business_type",
            "beneficiary_agent_code",
            "code",
            "designation",
            "gstin_number",
            "gst_type",
            "pan_number",
            "customer_name",
            "person_name",
            "email",
            "phone_number",
            "fax_number",
            "import_export_code",
            "trade_name",
            "website",
            "customer_type",
            "sales_executive",
            "sales_executive_assistant",
            "delivery_days",
            "udyam_no",
            "applicable_gst",
            "office_address_shop",
            "office_address_area",
            "office_address_landmark",
            "office_address_pin_code",
            "office_address_city",
            "office_address_state",
            "office_address_country",
            "factory_address_shop",
            "factory_address_area",
            "factory_address_landmark",
            "factory_address_pin_code",
            "factory_address_city",
            "factory_address_state",
            "factory_address_country",
            "is_company_visible_on_documents",
            "credit_limit",
            "due_days",
            "licence_no",
            "note",
            "customer_balance",
            "amount",
            "company_type",
        ]

class CustomerListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = ["id", "customer_name", "code"]


class SMManagerUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name"]
