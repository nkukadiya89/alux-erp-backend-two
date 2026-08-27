import django_filters
from .models import BlosterMaster, BlosterType


class BlosterTypeFilter(django_filters.FilterSet):

    name = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains"
    )

    status = django_filters.CharFilter(
        field_name="status", lookup_expr="iexact"
    )

    class Meta:
        model = BlosterType
        fields = ["name", "status"]


class BlosterMasterFilter(django_filters.FilterSet):

    bloster_no = django_filters.CharFilter(
        field_name="bloster_no", lookup_expr="icontains"
    )

    press = django_filters.NumberFilter(
        field_name="press"
    )

    type = django_filters.NumberFilter(
        field_name="type"
    )

    diameter_mm = django_filters.NumberFilter(
        field_name="diameter_mm"
    )

    thickness_mm = django_filters.NumberFilter(
        field_name="thickness_mm"
    )

    size = django_filters.NumberFilter(
        field_name="size"
    )

    created_at = django_filters.DateFromToRangeFilter(
        field_name="created_at"
    )

    class Meta:
        model = BlosterMaster
        fields = [
            "bloster_no",
            "press",
            "type",
            "diameter_mm",
            "thickness_mm",
            "size",
            "created_at",
        ]