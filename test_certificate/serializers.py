from test_certificate.models import TestCertificate
from common.serializers import BaseModelSerializer


class TestCertificateSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = TestCertificate
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "tc_date",
            "tc_no",
            "bundle_outward",
            "section_no",
            "length",
            "qty",
            "alloy",
            "temper",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)

        if instance.bundle_outward:
            response["bundle_outward"] = {
                "id": instance.bundle_outward.id,
                "slip_no": instance.bundle_outward.slip_no,
            }

        if instance.section_no:
            response["section_no"] = {
                "id": instance.section_no.id,
                "die_number": instance.section_no.die_number,
            }

        if instance.alloy:
            response["alloy"] = {
                "id": instance.alloy.id,
                "alloy_code": instance.alloy.alloy_code,
                "standard_name": instance.alloy.standard_name,
            }

        if instance.temper:
            response["temper"] = {
                "id": instance.temper.id,
                "name": instance.temper.name,
                "temper_code_new": instance.temper.temper_code_new,
            }

        return response
