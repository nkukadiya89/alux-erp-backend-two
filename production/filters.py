import django_filters
from django.db.models import Q
from datetime import datetime, time
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_date
from production.models import Production


class ProductionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    start_date = django_filters.CharFilter(method="filter_start_date")
    end_date = django_filters.CharFilter(method="filter_end_date")
    shift = django_filters.NumberFilter(field_name="shift_id")

    planning = django_filters.NumberFilter(field_name="planning_id")
    press = django_filters.NumberFilter(field_name="press_id")
    workorder = django_filters.NumberFilter(field_name="workorder_id")
    customer = django_filters.NumberFilter(field_name="customer_id")
    die_profile = django_filters.NumberFilter(field_name="die_profile_id")
    alloy = django_filters.NumberFilter(field_name="alloy_id")
    temper = django_filters.NumberFilter(field_name="temper_id")
    production_no = django_filters.CharFilter(
        field_name="production_no", lookup_expr="icontains"
    )
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")

    class Meta:
        model = Production
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        value = value.strip()
        return queryset.filter(
            Q(production_no__icontains=value)
            | Q(planning__planning_no__icontains=value)
            | Q(workorder__order_no__icontains=value)
            | Q(workorder__purchase_order_no__icontains=value)
            | Q(customer__customer_name__icontains=value)
            | Q(customer__code__icontains=value)
            | Q(die_profile__die_number__icontains=value)
            | Q(die_tool__tool_number__icontains=value)
            | Q(die_tool__drawing_no__icontains=value)
            | Q(press__name__icontains=value)
            | Q(press__code__icontains=value)
            | Q(alloy__alloy_code__icontains=value)
            | Q(temper__temper_code_new__icontains=value)
            | Q(quenching_type__icontains=value)
            | Q(status__icontains=value)
            | Q(completion_status__icontains=value)
            | Q(remarks__icontains=value)
            | Q(shift_name_snapshot__icontains=value)
            | Q(shift__shift_name__icontains=value)
        ).distinct()

    def filter_start_date(self, queryset, name, value):
        try:
            date_obj = parse_date(value)
            if date_obj:
                start_datetime = make_aware(datetime.combine(date_obj, time.min))
                return queryset.filter(created_at__gte=start_datetime)
        except Exception:
            pass
        return queryset

    def filter_end_date(self, queryset, name, value):
        try:
            date_obj = parse_date(value)
            if date_obj:
                end_datetime = make_aware(datetime.combine(date_obj, time.max))
                return queryset.filter(created_at__lte=end_datetime)
        except Exception:
            pass
        return queryset
