import django_filters
from django.db.models import Q
from datetime import datetime, time
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_date
from online_inspection.models import OnlineInspection


class OnlineInspectionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    inspection_date = django_filters.DateFilter(field_name="inspection_date")
    start_date = django_filters.CharFilter(method="filter_start_date")
    end_date = django_filters.CharFilter(method="filter_end_date")

    press = django_filters.NumberFilter(field_name="press_id")
    shift = django_filters.NumberFilter(field_name="shift_id")

    class Meta:
        model = OnlineInspection
        fields = []

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(inspection_date__icontains=value)
            | Q(press__name__icontains=value)
            | Q(shift_name_snapshot__icontains=value)
            | Q(qc_rack_details__rack_no__icontains=value)
            | Q(qc_rack_details__production__production_no__icontains=value)
        ).distinct()

    def filter_start_date(self, queryset, name, value):
        try:
            date_obj = parse_date(value)
            if date_obj:
                start_datetime = make_aware(datetime.combine(date_obj, time.min))
                return queryset.filter(inspection_date__gte=start_datetime)
        except Exception:
            pass
        return queryset

    def filter_end_date(self, queryset, name, value):
        try:
            date_obj = parse_date(value)
            if date_obj:
                end_datetime = make_aware(datetime.combine(date_obj, time.max))
                return queryset.filter(inspection_date__lte=end_datetime)
        except Exception:
            pass
        return queryset
