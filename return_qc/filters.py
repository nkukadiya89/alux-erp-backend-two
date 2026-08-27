import django_filters
from django.db.models import Q

from return_qc.models import ReturnQC


class ReturnQCFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    inspection_date = django_filters.DateFilter(field_name="inspection_date")
    vendor = django_filters.NumberFilter(field_name="vendor_id")
    overall_result = django_filters.CharFilter(field_name="overall_result")

    class Meta:
        model = ReturnQC
        fields = []

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(inspection_no__icontains=value)
            | Q(vehicle_no__icontains=value)
            | Q(gate_entry_ref__icontains=value)
            | Q(vendor__customer_name__icontains=value)
            | Q(vendor__code__icontains=value)
            | Q(jobwork_invoice__challan_no__icontains=value)
            | Q(qc_lines__production__production_no__icontains=value)
        ).distinct()
