import logging
from django_filters.rest_framework import DjangoFilterBackend
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from test_certificate.filters import TestCertificateFilter
from test_certificate.models import TestCertificate
from test_certificate.serializers import TestCertificateSerializer


class TestCertificateViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = TestCertificate.objects.select_related(
        "bundle_outward", "section_no", "alloy", "temper"
    ).order_by("-created_at")
    serializer_class = TestCertificateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TestCertificateFilter

    ordering_fields = [
        "id",
        "tc_date",
        "tc_no",
        "created_at",
        "updated_at",
    ]
