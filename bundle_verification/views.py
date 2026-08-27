from operator import itemgetter

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from bundle_inward.models import BundleInward, ExcessStock
from bundle_outward.models import BundleOutward
from bundle_verification.models import StockVerification
from common.models import ArchiveMixin
from customer.customer_master_views import BaseModelViewSet
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination


class StockVerificationViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = StockVerification.objects.all().order_by("-id")
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_avg_weight(self, die, length):
        try:
            length = length or 0
            wt_kg_p_mt = die.wt_kg_p_mt if die and die.wt_kg_p_mt else 0
            avg_weight = (length * wt_kg_p_mt) / 1000
            return round(avg_weight, 3)
        except Exception:
            return 0

    @action(detail=False, methods=["get"], url_path="get-verified-bundles-datetime")
    def get_verified_bundles_datetime(self, request, *args, **kwargs):
        try:
            stock_verifications = StockVerification.objects.all().select_related(
                "created_by"
            )
            search_query = request.query_params.get("search", "").lower()
            if search_query:
                stock_verifications = stock_verifications.filter(
                    Q(created_by__username__icontains=search_query)
                    | Q(id__icontains=search_query)
                )

            datetime_list = []
            for obj in stock_verifications:
                if obj.created_at:
                    datetime_list.append(
                        {"report_id": obj.id, "date_time": obj.created_at}
                    )

            ordering = request.query_params.get("ordering", "-report_id")
            reverse = ordering.startswith("-")
            ordering_key = ordering.lstrip("-")
            try:
                datetime_list = sorted(
                    datetime_list, key=itemgetter(ordering_key), reverse=reverse
                )
            except KeyError:
                return Response(
                    {
                        "success": False,
                        "message": f"Invalid ordering key: {ordering_key}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(datetime_list, request)

            return paginator.get_paginated_response(
                {"success": True, "data": paginated_data}
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["patch"], url_path="verify-bundles")
    def verify_bundles(self, request, *args, **kwargs):
        try:
            if not request.user or not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required to verify bundle.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            bundle_number = request.query_params.get("bundle_number")
            report_id = request.query_params.get("report_id")

            if not bundle_number:
                return Response(
                    {
                        "success": False,
                        "message": "bundle_no query parameter is required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                bundle = BundleInward.objects.get(bundle_no=bundle_number)
                bundle.verified = True
                bundle.verify_by = request.user
                bundle.verified_date = timezone.now()
                bundle.save()
                if report_id:
                    try:
                        stock_verification = StockVerification.objects.get(id=report_id)
                        existing_ids = (
                            stock_verification.verified_bundles.split(",")
                            if stock_verification.verified_bundles
                            else []
                        )
                        if str(bundle.id) not in existing_ids:
                            existing_ids.append(str(bundle.id))
                            stock_verification.verified_bundles = ",".join(existing_ids)

                        stock_verification.updated_by = request.user
                        stock_verification.updated_at = timezone.now()
                        stock_verification.save()

                    except StockVerification.DoesNotExist:
                        return Response(
                            {
                                "success": False,
                                "message": f"No StockVerification found with report_id '{report_id}'.",
                            },
                            status=status.HTTP_404_NOT_FOUND,
                        )

                else:
                    StockVerification.objects.create(
                        verified_bundles=str(bundle.id),
                        created_by=request.user,
                        created_at=timezone.now(),
                        updated_by=request.user,
                        updated_at=timezone.now(),
                    )

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="VERIFY",
                    module_name="Stock verification",
                    description=f"Verified bundles: {bundle_number}",
                    request=request,
                    payload=payload,
                )

                return Response(
                    {
                        "success": True,
                        "message": f"Bundle {bundle_number} verified successfully.",
                        "verified_bundle_id": bundle.id,
                    },
                    status=status.HTTP_200_OK,
                )

            except BundleInward.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": f"No bundle found with bundle_no '{bundle_number}'.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="get-verified-bundle")
    def get_verified_bundle(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "bundle_no")
            report_id = request.query_params.get("report_id")

            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            if report_id:
                try:
                    report = StockVerification.objects.get(id=report_id)
                    bundle_ids = [
                        int(bid.strip())
                        for bid in report.verified_bundles.split(",")
                        if bid.strip().isdigit()
                    ]
                    bundles = BundleInward.objects.filter(
                        id__in=bundle_ids, status="Packed", verified=True
                    ).select_related(
                        "workorder",
                        "workorder_detail__die_profile",
                        "workorder_detail__alloy",
                        "workorder__bill_to",
                    )
                except StockVerification.DoesNotExist:
                    return Response(
                        {"success": False, "message": "Invalid report_id"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                bundles = BundleInward.objects.filter(
                    status="Packed", verified=True
                ).select_related(
                    "workorder",
                    "workorder_detail__die_profile",
                    "workorder_detail__alloy",
                    "workorder__bill_to",
                )

            bundle_list = []
            total_weight = 0.0
            total_pieces = 0
            total_bundles = 0

            for bundle in bundles:
                die = None
                die_number = None
                length = None
                alloy_name = ""
                item_name = "No Dimensions Available"
                party_name = ""
                pieces = bundle.pieces
                weight = float(bundle.weight)

                if bundle.is_excess_stock:
                    excess_stock = ExcessStock.objects.filter(
                        bundle_inward=bundle
                    ).first()

                    if excess_stock:
                        die = excess_stock.die_profile
                        length = excess_stock.length
                        alloy = excess_stock.alloy
                        pieces = excess_stock.pieces
                        weight = float(excess_stock.weight)

                        if die:
                            die_number = die.die_number
                            dimensions = [
                                die.dimension1,
                                die.dimension2,
                                die.dimension3,
                                die.dimension4,
                            ]
                            item_name = " X ".join(
                                [f"{dim} MM" for dim in dimensions if dim]
                            )
                        else:
                            item_name = "No Dimensions Available"

                        if alloy:
                            alloy_name = (
                                f"{alloy.alloy_code} / {alloy.standard.name}"
                                if alloy.standard and alloy.color_code
                                else ""
                            )

                        party_name = "Excess Stock"
                else:
                    workorder = bundle.workorder
                    detail = bundle.workorder_detail

                    die = detail.die_profile if detail else None
                    length = detail.length if detail else None
                    alloy = detail.alloy if detail else None

                    if die:
                        die_number = die.die_number
                        dimensions = [
                            die.dimension1,
                            die.dimension2,
                            die.dimension3,
                            die.dimension4,
                        ]
                        item_name = " X ".join(
                            [f"{dim} MM" for dim in dimensions if dim]
                        )
                    else:
                        item_name = "No Dimensions Available"

                    if alloy:
                        alloy_name = (
                            f"{alloy.alloy_code} / {alloy.standard.name}"
                            if alloy.alloy_code and alloy.standard
                            else ""
                        )

                    party_name = (
                        workorder.bill_to.customer_name
                        if workorder and workorder.bill_to
                        else None
                    )

                avg_weight = self.get_avg_weight(die, length)

                row = {
                    "id": bundle.id,
                    "bundle_no": bundle.bundle_no,
                    "status": bundle.verified,
                    "die_profile": die_number,
                    "length": length,
                    "pieces": pieces,
                    "profile_description": item_name,
                    "weight": weight,
                    "avg_weight": avg_weight,
                    "alloy": (alloy_name),
                    "party": party_name,
                }

                if search_query:
                    if not any(
                        search_query in str(value).lower()
                        for value in row.values()
                        if value
                    ):
                        continue

                bundle_list.append(row)

                total_weight += weight
                total_pieces += pieces
                total_bundles += 1

            try:
                bundle_list = sorted(
                    bundle_list, key=itemgetter(ordering), reverse=reverse
                )
            except KeyError:
                pass

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(bundle_list, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "data": paginated_data,
                    "totals": {
                        "total_weight": round(total_weight, 2),
                        "total_pieces": total_pieces,
                        "total_bundles": total_bundles,
                    },
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="get-unverified-bundle")
    def get_unverified_bundle(self, request, *args, **kwargs):
        search_query = request.query_params.get("search", "").lower()
        ordering = request.query_params.get("ordering", "bundle_no")
        reverse = False
        if ordering.startswith("-"):
            ordering = ordering[1:]
            reverse = True

        bundles = BundleInward.objects.filter(
            status="Packed", verified=False
        ).select_related(
            "workorder",
            "workorder_detail__die_profile",
            "workorder_detail__alloy",
            "workorder__bill_to",
        )

        bundle_list = []
        total_weight = 0.0
        total_pieces = 0
        total_bundles = 0

        for bundle in bundles:
            die = None
            die_number = None
            length = None
            alloy_name = ""
            item_name = "No Dimensions Available"
            party_name = ""
            pieces = bundle.pieces
            weight = float(bundle.weight)

            if bundle.is_excess_stock:
                excess_stock = ExcessStock.objects.filter(bundle_inward=bundle).first()

                if excess_stock:
                    die = excess_stock.die_profile
                    length = excess_stock.length
                    alloy = excess_stock.alloy
                    pieces = excess_stock.pieces
                    weight = float(excess_stock.weight)

                    if die:
                        die_number = die.die_number
                        dimensions = [
                            die.dimension1,
                            die.dimension2,
                            die.dimension3,
                            die.dimension4,
                        ]
                        item_name = " X ".join(
                            [f"{dim} MM" for dim in dimensions if dim]
                        )
                    else:
                        item_name = "No Dimensions Available"

                    if alloy:
                        alloy_name = (
                            f"{alloy.alloy_code} / {alloy.standard.name}"
                            if alloy.alloy_code and alloy.standard
                            else ""
                        )

                    party_name = "Excess Stock"
            else:
                workorder = bundle.workorder
                detail = bundle.workorder_detail

                die = detail.die_profile if detail else None
                length = detail.length if detail else None
                alloy = detail.alloy if detail else None

                if die:
                    die_number = die.die_number
                    dimensions = [
                        die.dimension1,
                        die.dimension2,
                        die.dimension3,
                        die.dimension4,
                    ]
                    item_name = " X ".join([f"{dim} MM" for dim in dimensions if dim])
                else:
                    item_name = "No Dimensions Available"

                if alloy:
                    alloy_name = (
                        f"{alloy.alloy_code} / {alloy.standard.name}"
                        if alloy.alloy_code and alloy.standard
                        else ""
                    )

                party_name = (
                    workorder.bill_to.customer_name
                    if workorder and workorder.bill_to
                    else None
                )

            avg_weight = self.get_avg_weight(die, length)

            row = {
                "id": bundle.id,
                "bundle_no": bundle.bundle_no,
                "status": bundle.verified,
                "die_profile": die_number,
                "length": length,
                "pieces": pieces,
                "weight": weight,
                "avg_weight": avg_weight,
                "alloy": (alloy_name),
                "profile_description": item_name,
                "party": party_name,
            }

            if search_query:
                if not any(
                    search_query in str(value).lower()
                    for value in row.values()
                    if value
                ):
                    continue

            bundle_list.append(row)

            total_weight += weight
            total_pieces += pieces
            total_bundles += 1

        try:
            bundle_list = sorted(bundle_list, key=itemgetter(ordering), reverse=reverse)
        except KeyError:
            pass

        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(bundle_list, request)

        return paginator.get_paginated_response(
            {
                "success": True,
                "data": paginated_data,
                "totals": {
                    "total_weight": round(total_weight, 3),
                    "total_pieces": total_pieces,
                    "total_bundles": total_bundles,
                },
            }
        )


class DispatchVerificationViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = StockVerification.objects.all().order_by("-id")
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_avg_weight(self, die, length):
        try:
            length = length or 0
            wt_kg_p_mt = die.wt_kg_p_mt if die and die.wt_kg_p_mt else 0
            avg_weight = (length * wt_kg_p_mt) / 1000
            return round(avg_weight, 3)
        except Exception:
            return 0

    @action(detail=False, methods=["get"], url_path="get-slip-numbers")
    def get_slip_numbers(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "-id")
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            queryset = BundleOutward.objects.all()

            if search_query:
                queryset = queryset.filter(slip_no__icontains=search_query)
            slip_list = []
            for obj in queryset:
                slip_list.append(
                    {
                        "id": obj.id,
                        "slip_no": obj.slip_no,
                        "workorder_id": obj.workorder_id,
                        "dispatch_to": obj.dispatch_to,
                        "date_prepared": (
                            obj.date_prepared if obj.date_prepared else None
                        ),
                    }
                )

            try:
                slip_list = sorted(
                    slip_list, key=lambda x: x.get(ordering) or "", reverse=reverse
                )
            except KeyError:
                pass

            return Response(
                {"success": True, "data": slip_list}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="get-bundles-by-slip")
    def get_bundles_by_slip(self, request, *args, **kwargs):
        try:
            slip_no = request.query_params.get("slip_no", None)
            if not slip_no:
                return Response(
                    {"success": False, "message": "slip_no is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                bundle_outward = BundleOutward.objects.get(slip_no=slip_no)
            except BundleOutward.DoesNotExist:
                return Response(
                    {"success": False, "message": "Slip not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            finalized_bundles = bundle_outward.outward_bundles.all()
            if not finalized_bundles.exists():
                return Response(
                    {
                        "success": True,
                        "data": [],
                        "total_bundles": 0,
                        "verified_bundles": 0,
                        "unverified_bundles": 0,
                    }
                )

            bundles = finalized_bundles.select_related(
                "workorder", "workorder_detail__die_profile"
            )

            search_query = request.query_params.get("search", "").lower()
            if search_query:
                bundles = bundles.filter(
                    Q(bundle_no__icontains=search_query)
                    | Q(
                        workorder_detail__die_profile__die_number__icontains=search_query
                    )
                )

            ordering = request.query_params.get("ordering", "id")
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            bundles = sorted(
                bundles,
                key=lambda x: (
                    getattr(x, ordering, None)
                    if hasattr(x, ordering)
                    else getattr(x.workorder_detail.die_profile, ordering, None)
                ),
                reverse=reverse,
            )

            response_data = []
            verified_count = 0
            for bundle in bundles:
                detail = bundle.workorder_detail
                die_number = (
                    detail.die_profile.die_number
                    if detail and detail.die_profile
                    else None
                )
                length = detail.length if detail else None

                die = detail.die_profile
                if die:
                    dimensions = [
                        die.dimension1,
                        die.dimension2,
                        die.dimension3,
                        die.dimension4,
                    ]
                    item_name = " X ".join([f"{dim} MM" for dim in dimensions if dim])
                else:
                    item_name = "No Dimensions Available"

                if bundle.verified:
                    verified_count += 1

                row = {
                    "id": bundle.id,
                    "bundle_no": bundle.bundle_no,
                    "status": bundle.verified,
                    "die_profile": die_number,
                    "profile_description": item_name,
                    "length": length,
                    "pieces": bundle.pieces,
                    "weight": float(bundle.weight),
                }
                response_data.append(row)

            total_bundles = len(response_data)
            unverified_count = total_bundles - verified_count

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(response_data, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "data": paginated_data,
                    "total_bundles": total_bundles,
                    "verified_bundles": verified_count,
                    "unverified_bundles": unverified_count,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
