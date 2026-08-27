from rest_framework import serializers

from party.models import Party


class PartySerializers(serializers.ModelSerializer):

    class Meta:
        model = Party
        fields = [
            "id",
            "name",
            "sundry_group",
            "account_group",
            "customer_category",
            "customer_subcategory",
            "customer_type",
            "office_address",
            "registered_address",
            "shipping_address",
            "applicable_gst",
            "party_section_no",
            "bank_name",
            "bank_branch_name",
            "bank_branch_address",
            "bank_account_number",
            "bank_ifsc_code",
            "gst_no",
            "gst_type",
            "pan_number",
            "udhyam_no",
            "sgst_number",
            "cgst_number",
            "unique_id",
            "deleted",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }
