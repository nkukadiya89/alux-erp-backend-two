from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.utils.timezone import now
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from mechanical_test.filters import MechanicalTestFilter
from mechanical_test.models import MechanicalTest, MechanicalTestDetail
from mechanical_test.serializers import (
    MechanicalTestSerializer,
    MechanicalTestDetailSerializer,
)


class MechanicalTestViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = (
        MechanicalTest.objects.select_related(
            "ageing_batch_no",
            "created_by",
            "updated_by",
            "shift",
        )
        .prefetch_related(
            Prefetch(
                "test_details",
                queryset=MechanicalTestDetail.objects.filter(
                    deleted=False
                ).select_related(
                    "section_no",
                    "die_no",
                    "alloy",
                    "temper",
                    "production_no",
                ),
            )
        )
        .order_by("-created_at")
    )

    serializer_class = MechanicalTestSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MechanicalTestFilter

    ordering_fields = ["id", "qc_date"]

    @action(
        detail=False,
        methods=["get"],
        url_path="today-mechanical-test-report",
    )
    def today_mechanical_test_report(self, request):
        """
        Today's Mechanical Test report.
        Ageing-sourced and Production-sourced records are returned separately
        so the UI can render Heat No / Ageing Cycle only for Ageing blocks.
        """
        today = now().date()
        qs = self.filter_queryset(
            self.get_queryset().filter(deleted=False, qc_date=today)
        ).order_by("start_time", "id")

        ageing_qs = qs.filter(source_type="AGEING")
        production_qs = qs.filter(source_type="PRODUCTION")

        serializer = self.get_serializer
        return Response(
            {
                "success": True,
                "data": {
                    "date": today.isoformat(),
                    "has_data": qs.exists(),
                    "ageing_tests": serializer(ageing_qs, many=True).data,
                    "production_tests": serializer(production_qs, many=True).data,
                    "total_count": qs.count(),
                    "ageing_count": ageing_qs.count(),
                    "production_count": production_qs.count(),
                },
                "message": "Today mechanical test report fetched successfully.",
            },
            status=status.HTTP_200_OK,
        )


class MechanicalTestDetailViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = MechanicalTestDetail.objects.all().order_by("-created_at")
    serializer_class = MechanicalTestDetailSerializer
