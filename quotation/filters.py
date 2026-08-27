import django_filters
from django.db.models import Q
from quotation.models import Quotation


class QuotationFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="custom_search")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("id", "id"),
            ("customer__customer_name", "customer"),
            ("quotation_date", "quotation_date"),
            ("project_name", "project_name"),
            ("quotation_no", "quotation_no"),
            ("converted_date", "converted_date"),
            ("status", "status"),
            ("workorder_no", "workorder_no"),
        )
    )

    class Meta:
        model = Quotation
        fields = []

    def custom_search(self, queryset, name, value):
        return queryset.filter(
            Q(id__icontains=value)
            | Q(customer__customer_name__icontains=value)
            | Q(quotation_date__icontains=value)
            | Q(quotation_no__icontains=value)
            | Q(converted_date__icontains=value)
            | Q(status__icontains=value)
            | Q(workorder_no__icontains=value)
        )
