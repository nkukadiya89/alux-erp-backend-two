import django_filters
from django.db.models import Q
from .models import Transporter


class TransporterFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    party_name = django_filters.CharFilter(lookup_expr="icontains")
    party_code = django_filters.CharFilter(lookup_expr="icontains")
    city = django_filters.CharFilter(lookup_expr="icontains")
    mobile_no = django_filters.CharFilter(lookup_expr="icontains")
    email_id = django_filters.CharFilter(lookup_expr="icontains")
    balance_type = django_filters.ChoiceFilter(choices=Transporter.BALANCE_CHOICES)

    class Meta:
        model = Transporter
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            Q(party_name__icontains=value)
            | Q(party_code__icontains=value)
            | Q(mobile_no__icontains=value)
            | Q(city__icontains=value)
            | Q(balance_type__iexact=value)
            | Q(email_id__icontains=value)
        )
