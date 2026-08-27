import logging
import re

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.models import AuthGroupPermissionsModel, CustomGroup, User, UserGroupsModel
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination
from utils.role_permission import (
    get_group_permission_by_user,
    get_permission_by_group_ids,
    get_purticlare_permission,
)

from .serializers import CustomGroupSerializers, PermissionSerializers

logger = logging.getLogger("file")


class GroupViewSet(ModelViewSet):
    queryset = CustomGroup.objects.all().order_by("-id")
    serializer_class = CustomGroupSerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ["id", "name", "sequence"]
    ordering_fields = ["id", "name", "sequence"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        # try:
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def get_queryset(self):
        queryset = super().get_queryset()
        id: str = self.request.query_params.get("id")
        deleted = self.request.query_params.get("deleted", False)

        filters = {}
        if id:
            filters["id"] = id
        if deleted in ["true", "1"]:
            filters["deleted"] = 1
        elif deleted in ["false", "0"]:
            filters["deleted"] = 0

        queryset = queryset.filter(**filters)

        return queryset

    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_at"] = timezone.now()
        # data["updated_at"] = None
        # data["approved_at"] = None

        permissions_id = data.pop("permissions_id", [])
        if not permissions_id:
            return Response({"error": "Provide permissions_id"})

        group_name = data.get("name")
        if Group.objects.filter(name=group_name).exists():
            return Response(
                {"success": False, "message": "Group with this name already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CustomGroupSerializers(data=data)

        if serializer.is_valid():
            group = serializer.save(created_by=request.user)

            # Add permissions to the group
            if permissions_id:
                permissions = Permission.objects.filter(id__in=permissions_id)
                group.permissions.set(permissions)

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="User Group",
                description=f"Created group {group.group_name}",
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
    @action(detail=False, methods=["get"], url_path="archive-group-permissions-list")
    def archive_group_permissions_list(self, request, *args, **kwargs):
        user = request.user
        archive_group_list = CustomGroup.objects.filter(
            created_by=user.id, deleted=1
        ).order_by("-sequence")
        queryset = self.filter_queryset(archive_group_list)
        excluded_group_ids = [1, 2, 3]
        queryset = queryset.exclude(id__in=excluded_group_ids)

        self.pagination_class.page_size = int(request.query_params.get("pagesize", 10))
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")

        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_at"] = timezone.now()
        # data["approved_at"] = None

        instance = self.get_object()

        permissions_id = data.pop(
            "permissions_id", None
        )  # Get permissions_id from request data

        if permissions_id is not None and not permissions_id:
            return Response(
                {"error": "Provide valid permissions_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group_name = data.get("name")
        if (
            group_name
            and Group.objects.exclude(id=instance.id).filter(name=group_name).exists()
        ):
            return Response(
                {"success": False, "message": "Group with this name already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use serializer to validate and update the group instance
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            # Save the updated group instance
            instance = serializer.save(
                updated_by=request.user
            )  # Optionally track who updated the group

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="User Group",
                description=f"Updated group {instance.group_name}",
                request=request,
                payload=payload,
            )

            # Update the permissions if permissions_id was provided
            if permissions_id is not None:
                permissions = Permission.objects.filter(id__in=permissions_id)
                instance.permissions.set(permissions)  # Set the new permissions

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"], url_path="users-by-group")
    def get_users_by_group(self, request):
        group_id = request.query_params.get("group_id")

        if not group_id:
            return Response(
                {"success": False, "message": "group_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_ids = UserGroupsModel.objects.filter(group_id=group_id).values_list(
                "user_id", flat=True
            )
            users = User.objects.filter(id__in=user_ids).values(
                "id", "username", "first_name", "last_name"
            )

            user_list = [
                {
                    "id": user["id"],
                    "username": user["username"],
                    "full_name": f"{user['first_name']} {user['last_name']}".strip(),
                }
                for user in users
            ]

            return Response(
                {"success": True, "data": [{"group_id": group_id, "users": user_list}]}
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error retrieving users: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="users-by-group")
    def get_users_by_group(self, request):
        group_id = request.query_params.get("group_id")

        if not group_id:
            return Response(
                {"success": False, "message": "group_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_ids = UserGroupsModel.objects.filter(group_id=group_id).values_list(
                "user_id", flat=True
            )
            usernames = User.objects.filter(id__in=user_ids).values_list(
                "username", flat=True
            )

            return Response(
                {
                    "success": True,
                    "data": [{"group_id": group_id, "users": list(usernames)}],
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error retrieving users: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # Get the group instance

            if not instance:
                return Response(
                    {"error": "Group not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            instance.delete()  # Hard delete (permanent removal from DB)

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="User Group",
                description=f"Deleted group {instance.group_name}",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": "Group deleted permanently."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)


class AssignUserGroupViewSet(ModelViewSet):
    queryset = CustomGroup.objects.all()
    serializer_class = CustomGroupSerializers

    def create(self, request, *args, **kwargs):
        user_ids = request.data.get("user_id")
        user_list = User.objects.filter(pk__in=user_ids)
        group_id = request.data.get("group_id")
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return Response(
                {"success": False, "message": "Group does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(user_list) != len(user_ids):
            return Response(
                {"success": False, "message": "Users do not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for user in user_list:
            group.user_set.add(user)

        return Response(
            {"success": True, "message": "User assigned to group"},
            status=status.HTTP_200_OK,
        )


class PermissionViewSet(ModelViewSet):
    queryset = Permission.objects.filter(content_type_id__gt=5).order_by("id")
    serializer_class = PermissionSerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(
        detail=False,
        methods=["GET"],
        url_path="get-purticlare-permission",
        permission_classes=[AllowAny],
    )
    def get_purticlare_permission(self, request, *args, **kwargs):
        content_types = self.request.query_params.get("content_types")
        model_names = self.request.query_params.get("model_names")
        group_id = self.request.query_params.get("group_id")

        if not content_types:
            return Response({"success": False, "message": "Content Type Not Found"})

        if not model_names:
            return Response({"success": False, "message": "Model Name Not Found"})

        response = get_purticlare_permission(content_types, model_names, group_id)
        return Response({"success": True, "data": response}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="model-wise-permission")
    def model_wise_permission(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        app_label = self.request.query_params.get("app_label")
        model_name = self.request.query_params.get("model_name")

        if not app_label:
            return Response({"success": False, "message": "App Label Not Found"})

        if not model_name:
            return Response({"success": False, "message": "Model Name Not Found"})

        permission_list = queryset.filter(
            content_type=app_label, content_type__model=model_name
        )

        page = self.paginate_queryset(permission_list)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(permission_list, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["PATCH"], url_path="group-wise-permission")
    def group_wise_permission(self, request, *args, **kwargs):
        group_ids = request.data.get("group_ids")
        group_id = request.data.get("group_id")

        role_name = request.data.get("role_name")

        if group_ids:
            user_assigned_groups = None
            user_assigned_permissions = None
            try:
                if role_name:
                    role_permission = Group.objects.get(name=role_name)
                    user_assigned_groups = role_permission

            except Group.DoesNotExist:
                return Response(
                    {"success": False, "message": "Group not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response = get_permission_by_group_ids(
                group_ids, user_assigned_groups, user_assigned_permissions
            )
            return Response(
                {"success": True, "data": response}, status=status.HTTP_200_OK
            )

        elif group_id:
            fetched_permissions = AuthGroupPermissionsModel.objects.filter(
                group_id__in=group_id
            ).order_by("-id")

            permission_details = []
            for get_permission in fetched_permissions:
                codename = Permission.objects.get(
                    id=get_permission.permission.id
                ).codename
                custom_group = CustomGroup.objects.get(
                    group_ptr=get_permission.group.id
                )

                permission_info = {
                    "id": get_permission.id,
                    "group_id": get_permission.group.id,
                    "group_name": custom_group.group_name,
                    "content_type": get_permission.permission.content_type.id,
                    "model_name": get_permission.permission.content_type.model.capitalize(),
                    "codename": codename,
                }
                permission_details.append(permission_info)

            return Response(
                {"success": True, "data": permission_details}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": "Provide Valid Data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def list(self, request, *args, **kwargs):
        group_name = self.request.query_params.get("group_name")

        if group_name:
            permission_list = []
            permission_by_group = AuthGroupPermissionsModel.objects.filter(
                group__name=group_name
            )

            for permissions in permission_by_group:
                codename = Permission.objects.get(id=permissions.permission.id)
                permission_detail = {
                    "id": permissions.permission.id,
                    "name": permissions.permission.name,
                    "codename": codename.codename,
                    "content_type_id": permissions.permission.content_type.id,
                    "model": permissions.permission.content_type.model.capitalize(),
                }
                permission_list.append(permission_detail)
            return Response(
                {
                    "success": True,
                    "data": permission_list,
                },
                status=status.HTTP_200_OK,
            )

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class GetGroupPermissionViewSet(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializers
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        data = {}
        group_id = self.kwargs.get("id")
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            data["total_record"] = 0
            data["success"] = False
            data["message"] = "Group not found"
            data["data"] = []
            return Response(data=data, status=status.HTTP_404_NOT_FOUND)

        permission_list = {}

        for permission in group.permissions.all():
            app_label = permission.content_type.app_label
            codename = permission.codename

            if app_label in permission_list:
                permission_list[app_label].append(codename)
            else:
                permission_list[app_label] = [codename]

        data["total_record"] = len(permission_list)
        data["success"] = True
        data["message"] = "OK"
        data["data"] = permission_list
        return Response(data=data, status=status.HTTP_200_OK)


class AssignPermissionGroupViewSet(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializers

    def create(self, request, *args, **kwargs):
        group_id = request.data.get("group_id")
        codename_list = list(request.data.get("codename"))

        group = Group.objects.get(pk=group_id)
        for codename in codename_list:
            code_id = (
                Permission.objects.filter(codename=codename).values("id")[0].get("id")
            )
            group.permissions.add(code_id)

        group_permission = Permission.objects.filter(group=group)
        permission_list = {}
        for permission in group_permission:
            if permission.content_type.app_label in permission_list:
                permission_name = permission_list[permission.content_type.app_label]
                permission_list[permission.content_type.app_label] = ",".join(
                    [permission_name, permission.name.split(" ")[1]]
                )
            else:
                permission_list[permission.content_type.app_label] = (
                    permission.name.split(" ")[1]
                )

        return Response(
            {
                "success": True,
                "message": "Permission assigned to group",
                "response": permission_list,
            },
            status=status.HTTP_200_OK,
        )


class GetAllPermissionViewSet(ModelViewSet):
    def get_queryset(self):
        ALLOWED_PERMISSION_APPS = [
            "user",
            "common",
            "die",
            "production",
            "quotation",
            "workorder",
            "bloster",
            "vendor",
            "customer",
            "nalco",
            "die_quotation",
            "proforma",
            "bundle_inward",
            "bundle_outward",
            "planning",
            "aging",
            "warehouse",
            "bundle_verification",
            "product",
            "msg_logger",
            "inquiry",
            "inquiry_quotation",
            "inquiry_salesorder",
            "die_requisition",
            "die_requisition_detail",
            "shift",
            "online_inspection",
            "vehicle_master",
            "transporter",
            "vehicle_type",
            "first_weight_entry",
            "second_weight_entry",
            "manual_weight_entry",
            "customer_type",
            "alloy",
            "temper",
            "dietool_production",
        ]

        EXCLUDED_MODELS = [
            "authgroupmodel",
            "contenttypemodel",
            "authpermissionmodel",
            "authgrouppermissionsmodel",
            "usergroupsmodel",
            "group",
            "permission",
            "contenttype",
            "authgroup",
            "authpermission",
            "authgrouppermissions",
            "usergroups",
            "django_content_type",
            "country",
            "currency",
            "financialyearmodel",
            "packingtype",
            "item",
            "party",
            "workorderdetail",
            "quotationdetail",
            "keypersons",
            "bankdetails",
            "bankingdetails",
            "billingperson",
            "contactperson",
            "shipingperson",
            "gsttype",
            "userprofile",
            "bundleoutwarddetails",
            "stockverification",
            "proformadetails",
            "diequotationdetails",
            "inquirydetail",
            "inquiryquotationdetail",
            "inquirysalesorderdetail",
        ]

        allowed_content_types = ContentType.objects.filter(
            app_label__in=ALLOWED_PERMISSION_APPS
        ).exclude(model__in=EXCLUDED_MODELS)

        return Permission.objects.filter(
            content_type__in=allowed_content_types
        ).order_by("id")

    def list(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        queryset = self.filter_queryset(self.get_queryset())

        if user_id:
            group_ids = UserGroupsModel.objects.filter(user_id=user_id).values_list(
                "group_id", flat=True
            )
            permission_ids = AuthGroupPermissionsModel.objects.filter(
                group_id__in=group_ids
            ).values_list("permission_id", flat=True)
            queryset = queryset.filter(id__in=permission_ids)

            permission_names = [
                self._generate_clean_permission_name(perm) for perm in queryset
            ]
            return Response({"success": True, "data": {"permission": permission_names}})

        SKIP_CLEAN_NAMES = [
            "change_profile_over_weight",
            "download_user_pdf_copy",
            "download_user_excel_copy",
            "download_conversion_rate_pdf_copy",
            "download_conversion_rate_excel_copy",
            "print_profile_pdf_copy",
            "print_profile_workorder_report_pdf_copy",
            "download_profile_pdf_copy",
            "download_profile_excel_copy",
            "download_profile_category_pdf_copy",
            "download_profile_category_excel_copy",
            "download_profile_group_pdf_copy",
            "download_profile_group_excel_copy",
            "download_profile_press_pdf_copy",
            "download_profile_press_excel_copy",
            "download_profile_size_pdf_copy",
            "download_profile_size_excel_copy",
            "download_profile_sub_category_pdf_copy",
            "download_profile_sub_category_excel_copy",
            "download_profile_tool_pdf_copy",
            "download_profile_tool_excel_copy",
            "download_alloy_pdf_copy",
            "download_alloy_excel_copy",
            "download_temper_pdf_copy",
            "download_temper_excel_copy",
            "print_quotation_pdf_copy",
            "print_workorder_copy",
            "download_bolster_pdf_copy",
            "download_bolster_excel_copy",
            "download_vendor_pdf_copy",
            "download_vendor_excel_copy",
            "print_customer_workorder_report_pdf_copy",
            "download_customer_pdf_copy",
            "download_customer_excel_copy",
            "download_customer_type_pdf_copy",
            "download_customer_type_excel_copy",
            "download_nalco_rate_pdf_copy",
            "download_nalco_rate_excel_copy",
            "print_die_quotation_pdf_copy",
            "print_proforma_copy",
            "print_bundle_inward_copy",
            "download_bundle_inward_excel_copy",
            "print_current_stock_copy",
            "download_current_stock_excel_copy",
            "print_excess_stock_copy",
            "download_excess_stock_excel_copy",
            "print_bundle_outward_copy",
            "download_bundle_outward_excel_copy",
            "download_planning_pdf_copy",
            "download_planning_excel_copy",
            "download_planning_priority_pdf_copy",
            "download_planning_priority_excel_copy",
            "print_warehouse_bundle_outward_copy",
            "download_warehouse_bundle_outward_excel_copy",
            "print_warehouse_current_stock_copy",
            "download_warehouse_current_stock_excel_copy",
            "print_stock_verification_copy",
            "print_dispatch_verification_copy",
            "print_workorder_report",
            "download_workorder_report_excel_copy",
            "print_packing_report_copy",
            "download_packing_report_excel_copy",
            "print_packing_datewise_report_copy",
            "download_packing_datewise_report_excel_copy",
            "print_dispatch_report_copy",
            "download_dispatch_report_excel_copy",
            "download_proforma_excel_copy",
            "download_quotation_excel_copy",
            "download_die_quotation_excel_copy",
            "download_workorder_excel_copy",
            "print_workorder_copy",
            "print_production_copy",
            "print_packing_copy",
            "print_account_sales_copy",
            "print_inquiry_pdf_copy",
            "download_inquiry_excel_copy",
            "download_inquiry_pdf_copy",
            "download_inquiry_detail_excel_copy",
            "download_inquiry_detail_pdf_copy",
            "print_inquiry_quotation_pdf_copy",
            "download_inquiry_quotation_excel_copy",
            "download_inquiry_quotation_pdf_copy",
            "download_inquiry_quotation_detail_excel_copy",
            "download_inquiry_quotation_detail_pdf_copy",
            "print_inquiry_salesorder",
            "download_inquiry_salesorder_excel_copy",
            "download_inquiry_salesorder_pdf_copy",
            "print_inquiry_salesorder_detail",
            "download_inquiry_salesorder_detail_excel_copy",
            "download_inquiry_salesorder_detail_pdf_copy",
        ]

        response_data = {"success": True, "data": []}
        for perm in queryset:
            action = perm.codename.split("_")[0]
            if perm.codename in SKIP_CLEAN_NAMES:
                clean_name = perm.name
            else:
                clean_name = self._generate_clean_permission_name(perm)

            permission_data = {
                "id": perm.id,
                "name": clean_name,
                "codename": perm.codename,
                "content_type": perm.content_type_id,
                "panel": action,
            }
            response_data["data"].append(permission_data)

        return Response(response_data)

    def _generate_clean_permission_name(self, perm):
        """
        Generate a cleaner permission name.
        E.g., 'add_dietype' -> 'Add Die Type'
        """
        codename = perm.codename
        action = codename.split("_")[0].capitalize()

        # Try to get the model class name
        try:
            model_class = perm.content_type.model_class()
            raw_model = model_class.__name__ if model_class else perm.content_type.model
        except:
            raw_model = perm.content_type.model

        # Custom spacing rules (extend as needed)
        CUSTOM_SPACING = {
            "Diesize": "Die Size",
            "Diesubcategory": "Die Subcategory",
            "Dietool": "Die Tool",
            "Dietype": "Die Type",
            "Bundleinward": "Bundle Inward",
            "Bundleoutward": "Bundle Outward",
        }

        # First try custom mapping
        model_name = CUSTOM_SPACING.get(raw_model)

        if not model_name:
            # Else fallback: split PascalCase to spaced name
            model_name = re.sub(r"(?<!^)(?=[A-Z])", " ", raw_model).strip().title()

        return f"{action} {model_name}"


class CreateGroupWithPermissionsViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name", "sequence"]
    search_fields = ["name"]

    @action(detail=False, methods=["GET"], url_path="get-group-permission-by-user")
    def get_group_permission_by_user(self, request, *args, **kwargs):
        login_user = self.request.user
        groups = Group.objects.filter(user=login_user).values_list("id", flat=True)
        user_exclude_groups = []

        if login_user:

            custom_group = CustomGroup.objects.filter(group_ptr__in=groups).exclude(
                group_ptr__name__in=user_exclude_groups
            )
            exclude_group = CustomGroup.objects.filter(
                group_ptr__name__in=user_exclude_groups
            )

            response = get_group_permission_by_user(custom_group, exclude_group)

        return Response(
            {"success": True, "response": response}, status=status.HTTP_200_OK
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        search_param = self.request.query_params.get("search", None)
        ordering_param = self.request.query_params.get("ordering", None)

        if search_param:
            queryset = queryset.filter(name__icontains=search_param)

        if ordering_param:
            queryset = queryset.order_by(ordering_param)

        return queryset

    def list(self, request, *args, **kwargs):
        groups = self.get_queryset()
        group_list = []

        for group in groups:
            permissions = [
                {
                    "id": permission.id,
                    "permission": f"{permission.content_type.app_label}| {permission.name}",
                }
                for permission in group.permissions.all()
            ]

            custom_group = CustomGroup.objects.filter(group_name=group).first()
            group_list.append(
                {
                    "group_id": group.id,
                    "group_name": custom_group.group_name,
                    "sequence": custom_group.sequence if custom_group else None,
                    "permissions": permissions,
                }
            )

        return Response(
            {"success": True, "response": group_list}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        permissions = [
            {
                "id": permission.id,
                "permission": f"{permission.content_type.app_label} | {permission.name}",
            }
            for permission in instance.permissions.all()
        ]

        custom_group = CustomGroup.objects.filter(name=instance).first()

        group_data = {
            "group_id": instance.id,
            "group_name": custom_group.group_name,
            "role_family": (
                custom_group.role_family.id if custom_group.role_family else None
            ),
            "family_name": (
                custom_group.role_family.family_name
                if custom_group.role_family
                else None
            ),
            "sequence": custom_group.sequence if custom_group else None,
            "permissions": permissions,
        }

        return Response(
            {"success": True, "response": group_data}, status=status.HTTP_200_OK
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        group_name = request.data.get("group_name")
        permission_ids = request.data.get("permissions", [])

        # group = CustomGroup.objects.filter(group_name=group_name).exists()
        role_family_instance = None
        if role_family:
            try:
                role_family_instance = RoleFamily.objects.get(id=role_family)
            except RoleFamily.DoesNotExist:
                return Response(
                    {"success": False, "message": "Role Family Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if company_id:
            group_exists = CustomGroup.objects.filter(
                group_name=group_name, company_id=company_id
            ).exists()
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create the CustomGroup instance, which will automatically assign a sequence
            if group_name and group_name.replace(" ", "").isalpha():
                custom_group = CustomGroup(
                    name="company_" + str(company_id) + "_" + group_name,
                    group_name=group_name,
                    role_family=role_family_instance,
                    company_id=company_id,
                    created_by=request.user,
                )
                custom_group.save()
                user = User.objects.get(
                    company=company_id, employee__isnull=True, vendor__isnull=True
                ).id
                custom_group.user_set.add(user)

            else:
                return Response(
                    {
                        "success": False,
                        "message": "Group name should contain only characters",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif vendor_id:
            group_exists = CustomGroup.objects.filter(
                group_name=group_name, vendor_id=vendor_id
            ).exists()
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create the CustomGroup instance, which will automatically assign a sequence
            if group_name and group_name.replace(" ", "").isalpha():
                custom_group = CustomGroup(
                    name="vendor_" + str(vendor_id) + "_" + group_name,
                    group_name=group_name,
                    role_family=role_family_instance,
                    vendor_id=vendor_id,
                    created_by=request.user,
                )
                custom_group.save()
                user = User.objects.get(
                    vendor=vendor_id, employee__isnull=True, company__isnull=True
                ).id
                custom_group.user_set.add(user)

            else:
                return Response(
                    {
                        "success": False,
                        "message": "Group name should contain only characters",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            group_exists = CustomGroup.objects.filter(
                group_name=group_name, created_by=request.user
            ).exists()
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            custom_group = CustomGroup(
                name=group_name,
                group_name=group_name,
                created_by=request.user,
            )
            custom_group.save()
            user = User.objects.get(id=request.user.id).id
            custom_group.user_set.add(user)

        # Create the CustomGroup instance, which will automatically assign a sequence

        permissions = Permission.objects.filter(id__in=permission_ids)
        custom_group.permissions.set(permissions)

        permission_list = {}
        for permission in custom_group.permissions.all():
            if permission.content_type.app_label in permission_list:
                permission_name = permission_list[permission.content_type.app_label]
                permission_list[permission.content_type.app_label] = ",".join(
                    [permission_name, permission.name.split(" ")[1]]
                )
            else:
                permission_list[permission.content_type.app_label] = (
                    permission.name.split(" ")[1]
                )

        return Response(
            {
                "success": True,
                "message": "Group created and Permission assigned to Group",
                "id": custom_group.id,
                "group_name": group_name,
                "sequence": custom_group.sequence,
                "role_family": (
                    custom_group.role_family.family_name
                    if custom_group.role_family
                    else None
                ),
                "company": company_id,
                "vendor": vendor_id,
                "response": permission_list,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        group = self.get_object()
        group_name = request.data.get("group_name")
        role_family = request.data.get("role_family")
        permission_ids = request.data.get("permissions", [])
        company_id = request.data.get("company")
        vendor_id = request.data.get("vendor")
        group_id = kwargs.get("pk")

        role_family_instance = None
        if role_family:
            try:
                role_family_instance = RoleFamily.objects.get(id=role_family)
            except RoleFamily.DoesNotExist:
                return Response(
                    {"success": False, "message": "Role Family Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        group_instance = CustomGroup.objects.get(pk=group_id)
        if company_id:
            group_exists = (
                CustomGroup.objects.filter(group_name=group_name, company_id=company_id)
                .exclude(pk=group_id)
                .exists()
            )
            if group_exists:
                return Response(
                    {
                        "success": False,
                        "message": "Role name already exists with your Company",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            group_instance.name = "company_" + str(company_id) + "_" + group_name
            group_instance.group_name = group_name
            group_instance.role_family = role_family_instance
            group_instance.company_id = company_id
            group_instance.updated_by = request.user
            group_instance.save()

        elif vendor_id:
            group_exists = (
                CustomGroup.objects.filter(group_name=group_name, vendor_id=vendor_id)
                .exclude(pk=group_id)
                .exists()
            )
            if group_exists:
                return Response(
                    {
                        "success": False,
                        "message": "Role name already exists with your Company",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            group_instance.name = "vendor_" + str(vendor_id) + "_" + group_name
            group_instance.group_name = group_name
            group_instance.role_family = role_family_instance
            group_instance.vendor_id = vendor_id
            group_instance.updated_by = request.user
            group_instance.save()

        else:
            group_exists = (
                CustomGroup.objects.filter(
                    group_name=group_name, created_by=request.user
                )
                .exclude(pk=group_id)
                .exists()
            )
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            group_instance.name = group_name
            group_instance.group_name = group_name
            group_instance.updated_by = request.user
            group_instance.save()

        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)

        permission_list = {}
        for permission in group.permissions.all():
            if permission.content_type.app_label in permission_list:
                permission_name = permission_list[permission.content_type.app_label]
                permission_list[permission.content_type.app_label] = ",".join(
                    [permission_name, permission.name.split(" ")[1]]
                )
            else:
                permission_list[permission.content_type.app_label] = (
                    permission.name.split(" ")[1]
                )

        return Response(
            {
                "success": True,
                "message": "Group updated and Permission assigned to Group",
                "id": group_instance.id,
                "group_name": group_instance.group_name,
                "sequence": (
                    group_instance.sequence if group_instance.sequence else None
                ),
                "role_family": (
                    group_instance.role_family.family_name
                    if group_instance.role_family
                    else None
                ),
                "company": company_id,
                "vendor": vendor_id,
                "response": permission_list,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        instance.save()
        return Response(
            {"success": True, "message": "Role Deleted"}, status=status.HTTP_200_OK
        )


class DeleteGroupWithPermissionsViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        group_ids = request.data.get("group_ids", [])

        if not group_ids:
            return Response(
                {"message": "No group IDs provided for deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        groups = CustomGroup.objects.filter(id__in=group_ids)
        for group in groups:
            group.deleted = 1
            group.save()

        return Response(
            {"success": True, "message": "Groups Archive successfully"},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="restore-group-permissions")
    def restore_group_permissions(self, request, *args, **kwargs):
        group_ids = request.data.get("group_ids", [])

        if not group_ids:
            return Response(
                {"message": "No group IDs provided for deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        groups = CustomGroup.objects.filter(id__in=group_ids)
        for group in groups:
            group.deleted = 0
            group.save()

        return Response(
            {"success": True, "message": "Groups Restore successfully"},
            status=status.HTTP_200_OK,
        )
