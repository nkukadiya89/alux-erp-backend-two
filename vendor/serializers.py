import traceback

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from common.serializers import BaseModelSerializer
from vendor.models import BankDetails, KeyPersons, Vendor


class KeyPersonSerisalizer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = KeyPersons
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "person_name",
            "designation",
            "email",
            "contact_number",
        ]


class BankDetailsSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = BankDetails
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "bank_name",
            "bank_account_number",
            "bank_ifsc_code",
            "branch_address",
            "bank_ad_code",
            "beneficiary_swift_code",
        ]


class VendorListSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Vendor
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "vendor_registered_name",
            "gst_no",
            "udyam_aadhaar_no",
            "vendor_trade_name",
            "vendor_code_as_per_company_erp",
            "person_name",
            "designation",
            "phone",
            "email",
            "registered_business_address_area",
            "registered_business_address_building",
            "registered_business_address_landmark",
            "registered_business_address_city",
            "registered_business_address_country",
            "trading_address_building",
            "trading_address_area",
            "trading_address_landmark",
            "trading_address_city",
            "trading_address_country",
            "trading_address_pincode",
        ]


class VendorSerializer(BaseModelSerializer):
    keypersons = serializers.ListField(required=False)
    bankdetails = serializers.ListField(required=False)

    class Meta(BaseModelSerializer.Meta):
        model = Vendor
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "business_type",
            "import_export_code",
            "beneficiary_agent_code",
            "pan_number",
            "code",
            "fax_number",
            "website",
            "person_name",
            "designation",
            "email",
            "phone",
            "udyam_aadhaar_no",
            "udyam_aadhaar_no_verified",
            "vendor_registered_name",
            "vendor_trade_name",
            "gst_no",
            "gst_no_verified",
            "vendor_code_as_per_company_erp",
            "is_active",
            "status",
            "vendor_trade_name",
            "registered_business_address_building",
            "registered_business_address_area",
            "registered_business_address_landmark",
            "registered_business_address_pincode",
            "registered_business_address_state",
            "registered_business_address_city",
            "registered_business_address_country",
            "trading_address_building",
            "trading_address_area",
            "trading_address_landmark",
            "trading_address_pincode",
            "trading_address_state",
            "trading_address_city",
            "trading_address_country",
            "vendor_logo",
            "keypersons",
            "bankdetails",
        ]

    def run_validation(self, data):
        try:
            return super().run_validation(data)
        except serializers.ValidationError as e:
            error_detail = e.detail

            if isinstance(error_detail, dict):
                for field, messages in error_detail.items():
                    if (
                        isinstance(messages, list)
                        and "This field is required." in messages
                    ):
                        error_detail[field] = [f"{field} is required."]

            raise serializers.ValidationError(error_detail)

    def create(self, validated_data):
        try:
            with transaction.atomic():
                keypersons_data = validated_data.pop("keypersons", [])
                bank_details_data = validated_data.pop("bankdetails", [])

                business_type = validated_data.get("business_type")
                if business_type == "INDIAN":
                    validated_data["beneficiary_agent_code"] = None
                    validated_data["import_export_code"] = None
                else:
                    validated_data["gst_no"] = None
                    validated_data["pan_number"] = None
                    validated_data["udyam_aadhaar_no"] = None

                vendor_instance = Vendor.objects.create(**validated_data)

                keyperson_instances = []
                for keyperson_data in keypersons_data:
                    keyperson_data["vendor_id"] = vendor_instance.id
                    keyperson_data["created_by"] = self.context["request"].user
                    keyperson_data["created_at"] = timezone.now()
                    keyperson_instances.append(
                        KeyPersons.objects.create(**keyperson_data)
                    )

                bank_details_instances = []
                for bank_data in bank_details_data:
                    bank_data["vendor_id"] = vendor_instance.id
                    bank_data["created_by"] = self.context["request"].user
                    bank_data["created_at"] = timezone.now()
                    bank_details_instances.append(
                        BankDetails.objects.create(**bank_data)
                    )
                return vendor_instance
        except Exception:
            traceback.print_exc()
            raise

    def update(self, instance, validated_data):
        instance.person_name = validated_data.get("person_name", instance.person_name)
        instance.designation = validated_data.get("designation", instance.designation)
        instance.email = validated_data.get("email", instance.email)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.business_type = validated_data.get(
            "business_type", instance.business_type
        )
        instance.udyam_aadhaar_no = validated_data.get(
            "udyam_aadhaar_no", instance.udyam_aadhaar_no
        )
        instance.udyam_aadhaar_no_verified = validated_data.get(
            "udyam_aadhaar_no_verified", instance.udyam_aadhaar_no_verified
        )
        instance.vendor_registered_name = validated_data.get(
            "vendor_registered_name", instance.vendor_registered_name
        )
        instance.vendor_trade_name = validated_data.get(
            "vendor_trade_name", instance.vendor_trade_name
        )
        instance.gst_no = validated_data.get("gst_no", instance.gst_no)
        instance.gst_no_verified = validated_data.get(
            "gst_no_verified", instance.gst_no_verified
        )
        instance.vendor_code_as_per_company_erp = validated_data.get(
            "vendor_code_as_per_company_erp", instance.vendor_code_as_per_company_erp
        )
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.status = validated_data.get("status", instance.status)

        instance.registered_business_address_building = validated_data.get(
            "registered_business_address_building",
            instance.registered_business_address_building,
        )
        instance.registered_business_address_area = validated_data.get(
            "registered_business_address_area",
            instance.registered_business_address_area,
        )
        instance.registered_business_address_landmark = validated_data.get(
            "registered_business_address_landmark",
            instance.registered_business_address_landmark,
        )
        instance.registered_business_address_pincode = validated_data.get(
            "registered_business_address_pincode",
            instance.registered_business_address_pincode,
        )
        instance.registered_business_address_state = validated_data.get(
            "registered_business_address_state",
            instance.registered_business_address_state,
        )
        instance.registered_business_address_city = validated_data.get(
            "registered_business_address_city",
            instance.registered_business_address_city,
        )
        instance.registered_business_address_country = validated_data.get(
            "registered_business_address_country",
            instance.registered_business_address_country,
        )

        instance.trading_address_building = validated_data.get(
            "trading_address_building", instance.trading_address_building
        )
        instance.trading_address_area = validated_data.get(
            "trading_address_area", instance.trading_address_area
        )
        instance.trading_address_landmark = validated_data.get(
            "trading_address_landmark", instance.trading_address_landmark
        )
        instance.trading_address_pincode = validated_data.get(
            "trading_address_pincode", instance.trading_address_pincode
        )
        instance.trading_address_state = validated_data.get(
            "trading_address_state", instance.trading_address_state
        )
        instance.trading_address_city = validated_data.get(
            "trading_address_city", instance.trading_address_city
        )
        instance.trading_address_country = validated_data.get(
            "trading_address_country", instance.trading_address_country
        )

        instance.vendor_logo = validated_data.get("vendor_logo", instance.vendor_logo)
        instance.updated_by = validated_data.get("updated_by", instance.updated_by)
        instance.updated_at = timezone.now()

        key_person_data_list = validated_data.pop("keypersons", [])
        buyer_key_person_ids = []
        key_person_instances = []

        for key_person_data in key_person_data_list:
            key_person_id = key_person_data.get("id")
            buyer_key_person_ids.append(key_person_id)

            key_person_instance = None

            if key_person_id:
                try:
                    key_person_instance = KeyPersons.objects.get(id=key_person_id)
                except KeyPersons.DoesNotExist:
                    raise serializers.ValidationError(
                        {"message": "Key Person Not Found"}
                    )
            new_key_person_instance = None
            if not key_person_instance:
                new_key_person_instance = KeyPersons.objects.create(
                    vendor=instance,
                    person_name=key_person_data.get("person_name"),
                    designation=key_person_data.get("designation"),
                    email=key_person_data.get("email"),
                    contact_number=key_person_data.get("contact_number"),
                )
                key_person_instances.append(new_key_person_instance)

            else:
                key_person_instance.person_name = key_person_data["person_name"]
                key_person_instance.designation = key_person_data["designation"]
                key_person_instance.email = key_person_data["email"]
                key_person_instance.contact_number = key_person_data["contact_number"]
                key_person_instance.save()
                key_person_instances.append(key_person_instance)

        if len(buyer_key_person_ids) > 0:
            if new_key_person_instance:
                KeyPersons.objects.filter(vendor=instance).exclude(
                    id__in=buyer_key_person_ids
                ).exclude(id=new_key_person_instance.id).update(deleted=True)
            else:
                KeyPersons.objects.filter(vendor=instance).exclude(
                    id__in=buyer_key_person_ids
                ).update(deleted=True)

        bank_details_data_list = validated_data.pop("bankdetails", [])
        buyer_bank_details_ids = []
        bank_details_instances = []

        for bank_details_data in bank_details_data_list:
            bank_details_id = bank_details_data.get("id")
            buyer_bank_details_ids.append(bank_details_id)

            bank_details_instance = None

            if bank_details_id:
                try:
                    bank_details_instance = BankDetails.objects.get(id=bank_details_id)
                except BankDetails.DoesNotExist:
                    raise serializers.ValidationError(
                        {"message": "Bank Details Not Found"}
                    )

            new_bank_details_instance = None
            if not bank_details_instance:
                new_bank_details_instance = BankDetails.objects.create(
                    vendor=instance,
                    bank_name=bank_details_data.get("bank_name"),
                    bank_account_number=bank_details_data.get("bank_account_number"),
                    bank_ifsc_code=bank_details_data.get("bank_ifsc_code"),
                    branch_address=bank_details_data.get("branch_address"),
                    bank_ad_code=bank_details_data.get("bank_ad_code"),
                    beneficiary_swift_code=bank_details_data.get(
                        "beneficiary_swift_code"
                    ),
                )
                bank_details_instances.append(new_bank_details_instance)

            else:
                bank_details_instance.bank_name = bank_details_data["bank_name"]
                bank_details_instance.bank_account_number = bank_details_data[
                    "bank_account_number"
                ]
                bank_details_instance.bank_ifsc_code = bank_details_data[
                    "bank_ifsc_code"
                ]
                bank_details_instance.branch_address = bank_details_data[
                    "branch_address"
                ]
                bank_details_instance.bank_ad_code = bank_details_data["bank_ad_code"]
                bank_details_instance.beneficiary_swift_code = bank_details_data[
                    "beneficiary_swift_code"
                ]
                bank_details_instances.append(bank_details_instance)
                bank_details_instance.save()

        if len(buyer_bank_details_ids) > 0:
            if new_bank_details_instance:
                BankDetails.objects.filter(vendor=instance).exclude(
                    id__in=buyer_bank_details_ids
                ).exclude(id=new_bank_details_instance.id).update(deleted=True)
            else:
                BankDetails.objects.filter(vendor=instance).exclude(
                    id__in=buyer_bank_details_ids
                ).update(deleted=True)

        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        keypersons_data = []
        try:
            keypersons_data = KeyPersonSerisalizer(
                KeyPersons.objects.filter(vendor=instance, deleted=False), many=True
            ).data

        except KeyPersons.DoesNotExist:
            pass
        if not keypersons_data:
            keypersons_data = [
                {
                    "vendor": None,
                    "person_name": None,
                    "email": None,
                    "designation": None,
                    "contact_number": None,
                }
            ]

        bankdetail_data = []
        try:
            bankdetail_data = BankDetailsSerializer(
                BankDetails.objects.filter(vendor=instance, deleted=False), many=True
            ).data
        except BankDetails.DoesNotExist:
            pass
        if not bankdetail_data:
            bankdetail_data = [
                {
                    "id": None,
                    "vendor": None,
                    "bank_name": None,
                    "bank_account_number": None,
                    "bank_ifsc_code": None,
                    "branch_address": None,
                    "bank_ad_code": None,
                    "beneficiary_swift_code": None,
                }
            ]
        ret["keypersons"] = keypersons_data
        ret["bankdetails"] = bankdetail_data

        return ret


class VendorSortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id",
            "vendor_registered_name",
        ]
