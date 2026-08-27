import django_filters
from django.db.models import Q
from .models import DiePress


class DiePressFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    code = django_filters.CharFilter(lookup_expr="icontains")
    name = django_filters.CharFilter(lookup_expr="icontains")

    capacity = django_filters.NumberFilter()
    billet_diameter = django_filters.NumberFilter()
    billet_length_min = django_filters.NumberFilter()
    billet_length_max = django_filters.NumberFilter()
    billet_weight = django_filters.NumberFilter()
    billet_wt_factor = django_filters.NumberFilter()
    extrusion_length_min = django_filters.NumberFilter()
    extrusion_length_max = django_filters.NumberFilter()

    created_by = django_filters.CharFilter(
        field_name="created_by__first_name", lookup_expr="icontains"
    )

    class Meta:
        model = DiePress
        fields = [
            "code",
            "name",
            "capacity",
            "billet_diameter",
            "billet_length_min",
            "billet_length_max",
            "billet_weight",
            "billet_wt_factor",
            "extrusion_length_min",
            "extrusion_length_max",
            "created_by",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(id__icontains=value)
            | Q(code__icontains=value)
            | Q(name__icontains=value)
            | Q(capacity__icontains=value)
            | Q(billet_diameter__icontains=value)
            | Q(billet_length_min__icontains=value)
            | Q(billet_length_max__icontains=value)
            | Q(billet_weight__icontains=value)
            | Q(billet_wt_factor__icontains=value)
            | Q(extrusion_length_min__icontains=value)
            | Q(extrusion_length_max__icontains=value)
            | Q(created_by__first_name__icontains=value)
            | Q(created_by__last_name__icontains=value)
        ).distinct()
