from rest_framework import serializers
from common.serializers import BaseModelSerializer
from proforma.models import Proforma


class ProformaListSerializers(BaseModelSerializer):
    customer_name = serializers.CharField(
        source="customer.customer_name", read_only=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = Proforma
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "proforma_date",
            "proforma_no",
            "workorder_no",
            "customer_name",
            "freight_charges",
        ]
