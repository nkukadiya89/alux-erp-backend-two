import django_filters
from django.db.models import Q

from jobwork_invoice.models import JobworkInvoice


class JobworkInvoiceFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    challan_date = django_filters.DateFilter(field_name="challan_date")
    vendor = django_filters.NumberFilter(field_name="vendor_id")
    jobwork_type = django_filters.NumberFilter(field_name="jobwork_type_id")

    class Meta:
        model = JobworkInvoice
        fields = []

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(challan_no__icontains=value)
            | Q(vendor_invoice_no__icontains=value)
            | Q(vehicle_no__icontains=value)
            | Q(gate_pass_ref__icontains=value)
            | Q(vendor__customer_name__icontains=value)
            | Q(vendor__code__icontains=value)
            | Q(invoice_lines__production__production_no__icontains=value)
        ).distinct()
