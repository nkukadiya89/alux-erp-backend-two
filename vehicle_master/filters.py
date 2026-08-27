import django_filters
from django.db.models import Q
from .models import VehicleMaster


class VehicleMasterFilter(django_filters.FilterSet):
    vehicle_no = django_filters.CharFilter(lookup_expr="icontains")
    party_name = django_filters.NumberFilter(field_name="party_name__id")
    vehicle_type = django_filters.NumberFilter(field_name="vehicle_type__id")
    party_name_text = django_filters.CharFilter(
        field_name="party_name__party_name", lookup_expr="icontains"
    )
    vehicle_type_text = django_filters.CharFilter(
        field_name="vehicle_type__vehicle_type", lookup_expr="icontains"
    )
    tare_wt_min = django_filters.NumberFilter(field_name="tare_wt", lookup_expr="gte")
    tare_wt_max = django_filters.NumberFilter(field_name="tare_wt", lookup_expr="lte")
    search = django_filters.CharFilter(method="custom_search")

    class Meta:
        model = VehicleMaster
        fields = [
            "vehicle_no",
            "party_name",
            "vehicle_type",
            "tare_wt",
        ]

    def custom_search(self, queryset, name, value):
        return queryset.filter(
            Q(vehicle_no__icontains=value)
            | Q(party_name__party_name__icontains=value)
            | Q(vehicle_type__vehicle_type__icontains=value)
            | Q(tare_wt__icontains=value)
        )
