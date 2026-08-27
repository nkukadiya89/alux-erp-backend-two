import django_filters
from django.db.models import Q
from .models import DieQuotation


class DieQuotationFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    customer_name = django_filters.CharFilter(
        field_name="customer__customer_name", lookup_expr="icontains"
    )
    die_quotation_no = django_filters.CharFilter(lookup_expr="icontains")
    minimum_order_qty = django_filters.NumberFilter()
    die_right = django_filters.CharFilter(lookup_expr="icontains")
    quotation_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = DieQuotation
        fields = [
            "customer_name",
            "die_quotation_no",
            "minimum_order_qty",
            "die_right",
            "quotation_date",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(id__icontains=value)
            | Q(customer__customer_name__icontains=value)
            | Q(die_quotation_no__icontains=value)
            | Q(minimum_order_qty__icontains=value)
            | Q(die_right__icontains=value)
        )
