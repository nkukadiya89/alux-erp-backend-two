import django_filters
from django.db.models import Q
from .models import Customer


class CustomerFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    customer_name = django_filters.CharFilter(lookup_expr="icontains")
    person_name = django_filters.CharFilter(lookup_expr="icontains")
    email = django_filters.CharFilter(lookup_expr="icontains")
    phone_number = django_filters.CharFilter(lookup_expr="icontains")
    gstin_number = django_filters.CharFilter(lookup_expr="icontains")
    pan_number = django_filters.CharFilter(lookup_expr="icontains")
    city = django_filters.CharFilter(
        field_name="office_address_city", lookup_expr="icontains"
    )
    company_type = django_filters.CharFilter(method="filter_company_type")

    class Meta:
        model = Customer
        fields = []

    def filter_company_type(self, queryset, name, value):
        if not value:
            return queryset
        value = value.lower()
        if value == "customer_vendor":
            return queryset

        return queryset.filter(company_type=value)

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset

        value = value.strip()

        q_filter = (
            Q(customer_name__icontains=value)
            | Q(person_name__icontains=value)
            | Q(email__icontains=value)
            | Q(phone_number__icontains=value)
            | Q(code__icontains=value)
            | Q(trade_name__icontains=value)
            | Q(gstin_number__icontains=value)
            | Q(pan_number__icontains=value)
            | Q(udyam_no__icontains=value)
            | Q(licence_no__icontains=value)
            | Q(website__icontains=value)
            | Q(fax_number__icontains=value)
            | Q(business_type__icontains=value)
            | Q(company_type__icontains=value)
            | Q(note__icontains=value)
            | Q(office_address_city__icontains=value)
            | Q(factory_address_city__icontains=value)
            | Q(customer_type__name__icontains=value)
            | Q(sales_executive__first_name__icontains=value)
            | Q(sales_executive__last_name__icontains=value)
            | Q(sales_executive__email__icontains=value)
            | Q(contact_persons__contact_person_name__icontains=value)
            | Q(contact_persons__contact_person_mobile_number__icontains=value)
            | Q(contact_persons__contact_person_email__icontains=value)
            | Q(banking_details__bank_name__icontains=value)
            | Q(banking_details__bank_account_number__icontains=value)
            | Q(banking_details__bank_ifsc_code__icontains=value)
        )

        if value.isdigit():
            int_val = int(value)
            q_filter |= (
                Q(id=int_val)
                | Q(credit_limit=int_val)
                | Q(due_days=int_val)
                | Q(delivery_days=int_val)
            )

        try:
            float_val = float(value)
            q_filter |= Q(credit_limit=float_val)
        except ValueError:
            pass

        return queryset.filter(q_filter).distinct()
