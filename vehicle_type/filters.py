import django_filters
from django.db.models import Q
from .models import VehicleType


class VehicleTypeFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    vehicle_type = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = VehicleType
        fields = ["vehicle_type"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(id__icontains=value) | Q(vehicle_type__icontains=value)
        )
