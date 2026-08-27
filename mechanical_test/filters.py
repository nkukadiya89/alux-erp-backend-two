import django_filters
from django.db.models import Q
from mechanical_test.models import MechanicalTest


class MechanicalTestFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    qc_date = django_filters.DateFilter(field_name="qc_date")

    ageing_batch_no = django_filters.NumberFilter(field_name="ageing_batch_no_id")
    source_type = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = MechanicalTest
        fields = []

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(id__icontains=value)
            | Q(qc_date__icontains=value)
            | Q(source_type__icontains=value)
            | Q(ageing_batch_no__batch_no__icontains=value)
        ).distinct()
