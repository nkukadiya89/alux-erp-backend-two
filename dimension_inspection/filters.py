import django_filters
from django.db.models import Q
from dimension_inspection.models import DimensionInspection


class DimensionInspectionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    inspection_date = django_filters.DateFilter(field_name="inspection_date")
    start_date = django_filters.CharFilter(method="filter_start_date")
    end_date = django_filters.CharFilter(method="filter_end_date")

    production = django_filters.NumberFilter(field_name="production_id")
    workorder = django_filters.NumberFilter(field_name="workorder_id")
    customer = django_filters.NumberFilter(field_name="customer_id")
    section = django_filters.NumberFilter(field_name="section_id")
    alloy = django_filters.NumberFilter(field_name="alloy_id")
    temper = django_filters.NumberFilter(field_name="temper_id")
    press = django_filters.NumberFilter(field_name="press_id")

    class Meta:
        model = DimensionInspection
        fields = []

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(id__icontains=value)
            | Q(inspection_date__icontains=value)
            | Q(production__production_no__icontains=value)
            | Q(workorder__work_order_no__icontains=value)
            | Q(customer__customer_name__icontains=value)
            | Q(section__die_number__icontains=value)
            | Q(alloy__alloy_code__icontains=value)
            | Q(temper__name__icontains=value)
            | Q(press__name__icontains=value)
        ).distinct()
