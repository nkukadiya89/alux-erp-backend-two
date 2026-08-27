import django_filters
from django.db.models import Q
from .models import Proforma


class ProformaFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    proforma_no = django_filters.CharFilter(lookup_expr="icontains")
    freight_charges = django_filters.NumberFilter()
    proforma_date = django_filters.DateFromToRangeFilter()

    customer_name = django_filters.CharFilter(
        field_name="customer__customer_name", lookup_expr="icontains"
    )

    class Meta:
        model = Proforma
        fields = [
            "proforma_no",
            "freight_charges",
            "proforma_date",
            "customer_name",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(proforma_no__icontains=value)
            | Q(proforma_date__icontains=value)
            | Q(freight_charges__icontains=value)
            | Q(customer__customer_name__icontains=value)
        )
