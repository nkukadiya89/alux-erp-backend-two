import json


from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.forms import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.export_excel import ExportUtility

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from die.models import Die, DieInformation, SectionBallonDimensions
from die.serializers import DieWithBallonSerializer
from utils.log_activity import clean_payload, log_user_activity

from .serializers import DieWithBallonListSerializer

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from die.models import Die
from die.serializers import SectionBallonDimensions
from die.serializers import DieWithBallonListSerializer, DieWithBallonSerializer
from django.db.models import OuterRef, Subquery

class DieWithBallonViewSet(BaseModelViewSet, ArchiveMixin):
    latest_reference = (
        DieInformation.objects
        .filter(section=OuterRef("pk"))
        .order_by("-id")
        .values("reference_drawing_number")[:1]
    )
    queryset = (
        Die.objects.all()
        .select_related(
            "die_group", "die_category", "die_sub_category", "created_by", "updated_by"
        ).annotate(number_of_dietools=Count("dietool_die"))
        .annotate(
            drawing_reference_no=Subquery(latest_reference)
        )
        .prefetch_related(
            Prefetch(
                "ballon_drawing_dimensions",
                queryset=SectionBallonDimensions.objects.filter(deleted=False).order_by(
                    "balloon_no"
                ),
            )
        )
        .order_by("-created_at")
    )

    serializer_class = DieWithBallonSerializer
    list_serializer_class = DieWithBallonListSerializer
    fy_filtering_enabled = False

    search_fields = [
        "die_number",
        "dimension1",
        "dimension2",
        "dimension3",
        "dimension4",
        "min_wt_kg_p_mt",
        "wt_kg_p_mt",
        "front_end_process_loss_mm",
        "back_end_process_loss_mm",
        "stretching_head_loss_mm",
        "stretching_tail_loss_mm",
        "total_process_loss_mm",
        "total_process_loss_meter",
        "total_process_loss_kg",
        "max_wt_kg_p_mt",
        "die_group__name",
        "die_category__name",
        "die_sub_category__name",
        "customer_reference_number",
        "die_type",
        "remarks",
    ]
    ordering_fields = search_fields + [
        "die_group",
        "die_category",
        "die_sub_category",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        die_group = params.get("die_group") or params.get("groupId")
        if die_group:
            qs = qs.filter(die_group_id=die_group)

        die_category = params.get("die_category")
        if die_category:
            qs = qs.filter(die_category_id=die_category)

        die_sub_category = params.get("die_sub_category")
        if die_sub_category:
            qs = qs.filter(die_sub_category_id=die_sub_category)

        die_type = params.get("die_type")
        if die_type:
            qs = qs.filter(die_type__iexact=die_type)

        search = params.get("search")
        if search:
            filter_q = Q()
            filter_q |= Q(die_number__istartswith=search)
            filter_q |= Q(dimension1__istartswith=search)
            filter_q |= Q(dimension2__istartswith=search)
            filter_q |= Q(dimension3__istartswith=search)
            filter_q |= Q(dimension4__istartswith=search)
            filter_q |= Q(min_wt_kg_p_mt__istartswith=search)
            filter_q |= Q(max_wt_kg_p_mt__istartswith=search)
            filter_q |= Q(wt_kg_p_mt__istartswith=search)
            filter_q |= Q(die_group__name__istartswith=search)
            filter_q |= Q(die_category__name__istartswith=search)
            filter_q |= Q(die_sub_category__name__istartswith=search)
            filter_q |= Q(customer_reference_number__istartswith=search)
            filter_q |= Q(die_type__istartswith=search)
            filter_q |= Q(remarks__istartswith=search)
            qs = qs.filter(filter_q)

        return qs
    
    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "die_number",
            "dimension1",
            "dimension2",
            "dimension3",
            "dimension4",
            "min_wt_kg_p_mt",
            "wt_kg_p_mt",
            "max_wt_kg_p_mt",
            "die_group__name",
            "die_category__name",
            "die_sub_category__name",
            "die_diagram",
            "die_detail_diagram",
            "customer_approved_diagram",
            "autocad_drawing",
            "die_manufacturing",    
            "die_sop",
            "customer_reference_number",
            "die_type",
            "remarks",
            "front_end_process_loss_mm",
            "back_end_process_loss_mm",
            "stretching_head_loss_mm",
            "stretching_tail_loss_mm",
            "total_process_loss_mm",
            "total_process_loss_meter",
            "total_process_loss_kg",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Die Number", "die_number"),
            ("Dimension 1", "dimension1"),
            ("Dimension 2", "dimension2"),
            ("Dimension 3", "dimension3"),
            ("Dimension 4", "dimension4"),
            ("Min WT KG/MT", "min_wt_kg_p_mt"),
            ("WT KG/MT", "wt_kg_p_mt"),
            ("Max WT KG/MT", "max_wt_kg_p_mt"),
            ("Die Group", "die_group__name"),
            ("Die Category", "die_category__name"),
            ("Die Sub Category", "die_sub_category__name"),
            ("Die Diagram", "die_diagram"),
            ("Die Detail Diagram", "die_detail_diagram"),
            ("Customer Approved Diagram", "customer_approved_diagram"),
            ("Autocad Drawing", "autocad_drawing"),
            ("Die Manufacturing", "die_manufacturing"),
            ("Die SOP", "die_sop"),
            ("Customer Reference Number", "customer_reference_number"),
            ("Die Type", "die_type"),
            ("Remarks", "remarks"),
            ("Front End Process Loss MM", "front_end_process_loss_mm"),
            ("Back End Process Loss MM", "back_end_process_loss_mm"),
            ("Stretching Head Loss MM", "stretching_head_loss_mm"),
            ("Stretching Tail Loss MM", "stretching_tail_loss_mm"),
            ("Total Process Loss MM", "total_process_loss_mm"),
            ("Total Process Loss Meter", "total_process_loss_meter"),
            ("Total Process Loss KG", "total_process_loss_kg"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]

        return ExportUtility.export_excel(
            queryset=queryset,
            columns=columns,
            filename="die.xlsx",
            sheet_name="Die",
        )
  

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            raw_data = request.data.get("form_data")
            if not raw_data:
                return Response(
                    {
                        "success": False,
                        "message": "Missing 'form_data' field.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                return Response(
                    {"success": False, "message": "Invalid JSON format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            main_errors = {}
            detail_errors = []

            balloon_data = data.get("balloon_drawing_dimensions", None)
            extrusion_data = data.get("extrusion_die_info", None)

            if balloon_data is not None:
                seen_balloon = set()
                for index, item in enumerate(balloon_data):
                    balloon_no = item.get("balloon_no")

                    if not balloon_no:
                        detail_errors.append(
                            {"row": index, "balloon_no": "This field is required."}
                        )
                        continue

                    if balloon_no in seen_balloon:
                        detail_errors.append(
                            {
                                "row": index,
                                "balloon_no": balloon_no,
                                "error": "Duplicate balloon_no found.",
                            }
                        )
                    else:
                        seen_balloon.add(balloon_no)

            serializer = self.get_serializer(data=data, context={"request": request})

            if not serializer.is_valid():
                main_errors.update(serializer.errors)

            instance = None
            if not (main_errors or detail_errors):
                instance = serializer.save()

            file_fields = [
                "die_diagram",
                "die_detail_diagram",
                "customer_approved_diagram",
                "autocad_drawing",
                "die_manufacturing",
                "die_sop",
            ]

            uploaded_files = {
                f: request.FILES.get(f) for f in file_fields if request.FILES.get(f)
            }

            if instance and uploaded_files:
                try:
                    instance.upload_doc(uploaded_files)
                    instance.refresh_from_db()
                except ValidationError as upload_error:
                    main_errors["files"] = (
                        upload_error.message_dict
                        if hasattr(upload_error, "message_dict")
                        else str(upload_error)
                    )

            if main_errors or detail_errors:
                response_data = {}

                if main_errors:
                    response_data.update(main_errors)

                if detail_errors:
                    response_data["balloon_drawing_dimensions"] = detail_errors

                return Response(
                    {
                        "success": False,
                        "message": "Invalid die data",
                        "errors": response_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Die",
                description=f"Created Die '{instance.die_number}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": self.get_serializer(instance).data},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            raw_data = request.data.get("form_data")
            if not raw_data:
                return Response(
                    {"success": False, "message": "Missing 'form_data' field."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                return Response(
                    {"success": False, "message": "Invalid JSON format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance = self.get_object()

            main_errors = {}
            detail_errors = []

            balloon_data = data.get("balloon_drawing_dimensions", None)

            seen_balloon = set()
            for index, item in enumerate(balloon_data):
                balloon_no = item.get("balloon_no")

                if not balloon_no:
                    detail_errors.append(
                        {"row": index, "balloon_no": "This field is required."}
                    )
                    continue

                if balloon_no in seen_balloon:
                    detail_errors.append(
                        {
                            "row": index,
                            "balloon_no": balloon_no,
                            "error": "Duplicate balloon_no found.",
                        }
                    )
                else:
                    seen_balloon.add(balloon_no)

            serializer = self.get_serializer(
                instance, data=data, partial=True, context={"request": request}
            )

            if not serializer.is_valid():
                main_errors.update(serializer.errors)

            if not (main_errors or detail_errors):
                instance = serializer.save()

            file_fields = [
                "die_diagram",
                "die_detail_diagram",
                "customer_approved_diagram",
                "autocad_drawing",
                "die_manufacturing",
                "die_sop",
            ]

            uploaded_files = {
                f: request.FILES.get(f) for f in file_fields if request.FILES.get(f)
            }

            if instance and uploaded_files:
                try:
                    instance.upload_doc(uploaded_files)
                    instance.refresh_from_db()
                except ValidationError as upload_error:
                    main_errors["files"] = (
                        upload_error.message_dict
                        if hasattr(upload_error, "message_dict")
                        else str(upload_error)
                    )

            if main_errors or detail_errors:
                response_data = {}

                if main_errors:
                    response_data.update(main_errors)

                if detail_errors:
                    response_data["balloon_drawing_dimensions"] = detail_errors

                return Response(
                    {
                        "success": False,
                        "message": "Invalid die data",
                        "errors": response_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Die",
                description=f"Updated Die '{instance.die_number}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": self.get_serializer(instance).data},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["patch"], url_path="upload-file")
    def upload_file(self, request, pk=None):
        try:
            die = Die.objects.get(id=pk, deleted=False)
        except Die.DoesNotExist:
            return Response({"success": False, "message": "Die not found."}, status=404)

        file_fields = [
            "die_diagram",
            "die_detail_diagram",
            "customer_approved_diagram",
            "autocad_drawing",
            "die_manufacturing",
            "die_sop",
        ]

        uploaded_field = None
        uploaded_file = None
        for field in file_fields:
            if field in request.FILES:
                uploaded_field = field
                uploaded_file = request.FILES[field]
                break

        if not uploaded_field:
            return Response(
                {"success": False, "message": "Please upload exactly one file."},
                status=400,
            )

        try:
            die.upload_doc({uploaded_field: uploaded_file})
            file_url = getattr(die, uploaded_field)
            return Response(
                {
                    "success": True,
                    "message": f"{uploaded_field} uploaded successfully.",
                    uploaded_field: file_url,
                },
                status=200,
            )
        except ValidationError as e:
            return Response({"success": False, "message": str(e)}, status=400)