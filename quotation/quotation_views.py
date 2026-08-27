from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.response import Response
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from die.models import Die
from quotation.filters import QuotationFilter
from quotation.models import Quotation, QuotationDetail
from quotation.serializers import (
    QuotationDetailSerializers,
    QuotationListSerializers,
    QuotationSerializers,
)
from utils.log_activity import clean_payload, log_user_activity


class QuotationViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Quotation.objects.all()
        .select_related("customer", "created_by")
        .prefetch_related(
            "quotation_quotation_detail", "quotation_quotation_detail__jobworks"
        )
        .order_by("-id")
    )
    serializer_class = QuotationSerializers
    list_serializer_class = QuotationListSerializers
    filter_backends = [DjangoFilterBackend]
    filterset_class = QuotationFilter

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_by"] = request.user.id
        data["created_at"] = timezone.now()
        data["updated_at"] = None

        serializer = self.serializer_class(data=data, context={"request": request})

        quotation_details_data = data.get("quotation_details", [])
        seen_combinations = set()

        if quotation_details_data:
            for detail in quotation_details_data:
                die_profile_id = detail.get("die_profile")
                length = detail.get("length")

                if die_profile_id is not None and length is not None:
                    combination = (die_profile_id, length)
                    die_profile = Die.objects.filter(id=die_profile_id).first()
                    if not die_profile:
                        die_number = die_profile.die_number if die_profile else "NA"

                    if combination in seen_combinations:
                        return Response(
                            {
                                "success": False,
                                "message": f"Duplicate entry found for die_profile ID {die_number} and length {length} in the same quotation.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    seen_combinations.add(combination)

        if serializer.is_valid():
            instance = serializer.save()

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Quotation",
                description=f"Created Quotation '{instance.quotation_no}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_by"] = request.user.id
        data["updated_at"] = timezone.now()

        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=data, partial=True, context={"request": request}
        )

        quotation_details_data = data.get("quotation_details", [])
        seen_combinations = set()

        if quotation_details_data:
            for detail in quotation_details_data:
                die_profile_id = detail.get("die_profile")
                length = detail.get("length")

                if die_profile_id is not None and length is not None:
                    combination = (die_profile_id, length)

                    if combination in seen_combinations:
                        return Response(
                            {
                                "success": False,
                                "message": f"Duplicate entry found for die_profile ID {die_profile_id} and length {length} in the same quotation.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    seen_combinations.add(combination)

        if serializer.is_valid():
            instance = serializer.save()

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Quotation",
                description=f"Updated Quotation '{instance.quotation_no}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_202_ACCEPTED,
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class QuotationDetailViewSet(BaseModelViewSet):
    queryset = QuotationDetail.objects.filter(deleted=False)
    serializer_class = QuotationDetailSerializers
