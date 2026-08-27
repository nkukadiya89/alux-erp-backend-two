import django_filters
from django.db.models import Q
from test_certificate.models import TestCertificate


class TestCertificateFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    tc_date = django_filters.DateFilter(field_name="tc_date")
    start_date = django_filters.CharFilter(method="filter_start_date")
    end_date = django_filters.CharFilter(method="filter_end_date")

    bundle_outward = django_filters.NumberFilter(field_name="bundle_outward_id")
    section_no = django_filters.NumberFilter(field_name="section_no_id")
    alloy = django_filters.NumberFilter(field_name="alloy_id")
    temper = django_filters.NumberFilter(field_name="temper_id")
    tc_no = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = TestCertificate
        fields = []

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(id__icontains=value)
            | Q(tc_no__icontains=value)
            | Q(tc_date__icontains=value)
            | Q(bundle_outward__slip_no__icontains=value)
            | Q(section_no__die_number__icontains=value)
            | Q(alloy__alloy_code__icontains=value)
            | Q(temper__name__icontains=value)
        ).distinct()
