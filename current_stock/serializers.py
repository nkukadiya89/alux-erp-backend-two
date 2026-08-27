from rest_framework import serializers
from current_stock.models import CurrentStock
class CurrentStockSerializer(serializers.ModelSerializer):

    class Meta:
        model = CurrentStock
        fields = ["id", "customer", "packed_weight"]
