from rest_framework import serializers

from common.models import JobWorkType, SectionType
from common.serializers import SectionTypeSerializer
from inquiry.models import Inquiry, InquiryDetail, InquiryDetailDrawing
from product.models import Alloy, StandardMaster, Temper
from user.models import User
from user.serializers import UserQuickSerializer
from product.serializers import StandardMasterSerializer

class InquiryDetailSortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ["id", "inquiry_number", "customer_name"]


class AlloySerializer(serializers.ModelSerializer):
    standard = StandardMasterSerializer(read_only=True)
    class Meta:
        model = Alloy
        fields = ["id", "alloy_code", "color_code", "standard"]


class SectionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionType
        fields = ["name"]

class StandardMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardMaster
        fields = ["name"]


class TemperSerializer(serializers.ModelSerializer):
    standard = StandardMasterSerializer(read_only=True)
    section_type = SectionTypeSerializer(read_only=True)
    class Meta:
        model = Temper
        fields = ["id", "temper_code_new", "standard", "section_type"]


class JobWorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobWorkType
        fields = ["id", "name"]


class InquiryDetailDrawingSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryDetailDrawing
        fields = ["id", "file_path"]


class InquiryDetailCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryDetail
        fields = [
            "id",
            "section_no",
            "description",
            "standard_confirmation",
            "standard_confirmation_other",
            "alloy",
            "temper",
            "length",
            "tolerance",
            "tolerance_plus",
            "tolerance_minus",
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
            "laser_marking_price",
            "laser_marking_description",
            "post_operation",
            "post_operation_other",
            "end_application",
        ]

class TrimmedDecimalField(serializers.DecimalField):
    def to_representation(self, value):
        if value is None:
            return None

        value = super().to_representation(value)
        return value.rstrip("0").rstrip(".")   

class InquiryDetailSerializer(serializers.ModelSerializer):
    length = TrimmedDecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True   )
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    inquiry_detail = InquiryDetailSortSerializer(source="inquiry", read_only=True)
    drawings = InquiryDetailDrawingSerializer(many=True, read_only=True)
    alloy_detail = AlloySerializer(source="alloy", read_only=True)
    temper_detail = TemperSerializer(source="temper", read_only=True)
    surface_finish_detail = JobWorkTypeSerializer(
        source="surface_finish", read_only=True, many=True
    )

    class Meta:
        model = InquiryDetail
        fields = [
            "id",
            "inquiry",
            "inquiry_detail",
            "section_no",
            "description",
            "drawings",
            "standard_confirmation",
            "standard_confirmation_other",
            "alloy",
            "alloy_detail",
            "surface_finish_detail",
            "temper",
            "temper_detail",
            "length",
            "tolerance",
            "tolerance_plus",
            "tolerance_minus",
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
            "laser_marking_price",
            "laser_marking_description",
            "post_operation",
            "post_operation_other",
            "end_application",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted",
        ]
    def get_inquiry_detail(self, obj):
        if obj.inquiry:
            return {
                "id": obj.inquiry.id,
                "inquiry_number": obj.inquiry.inquiry_number,
                "customer_name": obj.inquiry.customer_name,
            }
        return None


class InquiryCreateSerializer(serializers.ModelSerializer):
    inquiry_details = InquiryDetailCreateSerializer(many=True, required=False)
    assigned_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Inquiry
        fields = [
            "customer_name",
            "contact_persons",
            "initial_requirement",
            "annual_requirement",
            "inquiry_source",
            "status",
            "regret_reason",
            "special_notes",
            "certifications_required",
            "packaging_requirements",
            "additional_notes",
            "assigned_user",
            "inquiry_details",
        ]

    def validate_contact_persons(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("contact_persons must be a list")
        return value

    def create(self, validated_data):
        inquiry_details_data = validated_data.pop("inquiry_details", [])
        inquiry = Inquiry.objects.create(**validated_data)

        self.context["inquiry_details_data"] = inquiry_details_data

        return inquiry


class InquiryListSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    assigned_user_details = UserQuickSerializer(source="assigned_user", read_only=True)
    contact_persons = serializers.SerializerMethodField()
        
    class Meta:
        model = Inquiry
        fields = [
            "id",
            "inquiry_number",
            "inquiry_date",
            "customer_name",
            "contact_persons",
            "status",
            "inquiry_source",
            "assigned_user_details",  
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_contact_persons(self, obj):
        contact_persons = obj.contact_persons or []
        formatted_contacts = []
        for person in contact_persons:
            if not isinstance(person, dict):
                continue
            mobile = person.get("mobile", "")
            if mobile and not mobile.startswith("+"):
                person["mobile"] = f"+{mobile}"
            formatted_contacts.append(person)
        return formatted_contacts


class InquirySerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    assigned_user_detail = UserQuickSerializer(source="assigned_user", read_only=True)
    inquiry_details = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "inquiry_number",
            "inquiry_date",
            "customer_name",
            "contact_persons",
            "initial_requirement",
            "annual_requirement",
            "inquiry_source",
            "source_attachment",
            "feasiblity_description",
            "feasiblity_attachment",
            "status",
            "regret_reason",
            "special_notes",
            "certifications_required",
            "packaging_requirements",
            "additional_notes",
            "assigned_user",
            "assigned_user_detail",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",
            "inquiry_details",
        ]
        read_only_fields = ["inquiry_number", "inquiry_date", "source_attachment"]

    def get_inquiry_details(self, obj):
        inquiry_details = obj.inquiry_details.filter(deleted=False)
        return InquiryDetailSerializer(inquiry_details, many=True).data
