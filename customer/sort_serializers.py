from rest_framework import serializers
from customer.models import BankingDetails, ContactPerson, Customer, CustomerType
from user.models import User


class CustomerTypeSortSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerType
        fields = [
            "id",
            "name",
        ]


class ContactPersonSortSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContactPerson
        fields = [
            "id",
            "contact_person_name",
            "contact_person_designation",
            "contact_person_mobile_number",
            "contact_person_email",
        ]


class BankingDetailSortSerializer(serializers.ModelSerializer):

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


class CustomerSortSerializer(serializers.ModelSerializer):
    office_address = serializers.SerializerMethodField()
    factory_address = serializers.SerializerMethodField()
    customer_banking_details = serializers.SerializerMethodField()
    customer_contact_persons = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "gstin_number",
            "customer_name",
            "gst_type",
            "pan_number",
            "trade_name",
            "code",
            "person_name",
            "email",
            "phone_number",
            "applicable_gst",
            "office_address",
            "factory_address",
            "customer_banking_details",
            "customer_contact_persons",
            "is_company_visible_on_documents",
            "credit_limit",
            "due_days",
            "licence_no",
            "note",
            "customer_balance",
            "amount",
            "company_type",
        ]

    def get_office_address(self, obj):
        return {
            "shop": obj.office_address_shop,
            "area": obj.office_address_area,
            "landmark": obj.office_address_landmark,
            "pin_code": obj.office_address_pin_code,
            "city": obj.office_address_city,
            "state": obj.office_address_state,
            "country": obj.office_address_country,
        }

    def get_factory_address(self, obj):
        return {
            "shop": obj.factory_address_shop,
            "area": obj.factory_address_area,
            "landmark": obj.factory_address_landmark,
            "pin_code": obj.factory_address_pin_code,
            "city": obj.factory_address_city,
            "state": obj.factory_address_state,
            "country": obj.factory_address_country,
        }

    def get_customer_banking_details(self, obj):
        banking_details = BankingDetails.objects.filter(customer=obj, deleted=0)
        return BankingDetailSortSerializer(banking_details, many=True).data

    def get_customer_contact_persons(self, obj):
        contact_persons = ContactPerson.objects.filter(customer=obj, deleted=0)
        return ContactPersonSortSerializer(contact_persons, many=True).data

class SalesExecutiverUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name"]

class CustomerSortListSerializer(serializers.ModelSerializer):
    sales_executive = SalesExecutiverUserSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = [
            "id", 
            "customer_name",
            "gstin_number",
            "pan_number", 
            "code",
            "applicable_gst",
            "person_name",
            "email",
            "phone_number",
            "office_address_shop",
            "office_address_area",
            "office_address_landmark",
            "office_address_pin_code",
            "office_address_city",
            "office_address_state",
            "office_address_country",   
            "sales_executive"  
        ]

class CustomerBillToSerializer(serializers.ModelSerializer):
    sales_executive = SalesExecutiverUserSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = [
            "id", 
            "customer_name",
            "gstin_number",
            "pan_number", 
            "code",
            "applicable_gst",
            "person_name",
            "email",
            "phone_number",
            "office_address_shop",
            "office_address_area",
            "office_address_landmark",
            "office_address_pin_code",
            "office_address_city",
            "office_address_state",
            "office_address_country",   
            "sales_executive"  
        ]

class CustomerShipToSerializer(serializers.ModelSerializer):
    sales_executive = SalesExecutiverUserSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = [
            "id", 
            "customer_name",
            "gstin_number",
            "pan_number", 
            "code",
            "applicable_gst",
            "person_name",
            "email",
            "phone_number",
            "factory_address_shop",
            "factory_address_area",
            "factory_address_landmark",
            "factory_address_pin_code",
            "factory_address_city",
            "factory_address_state",
            "factory_address_country",   
            "sales_executive"  
        ]

