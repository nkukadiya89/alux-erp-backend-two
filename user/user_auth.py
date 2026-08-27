from collections import defaultdict
from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.utils.timezone import now
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from user.models import User
from utils.financial_year_data import set_default_financial_year
from utils.log_activity import log_user_activity


def get_user_permissions(user):
    project_apps = {
        "user",
        "common",
        "msg_logger",
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
        "inquiry",
        "inquiry_quotation",
        "inquiry_salesorder",
        "store",
        "die_requisition",
        "online_inspection",
        "dimension_inspection",
        "transporter",
        "vehicle_type",
        "vehicle_master",
        "material",
        "first_weight_entry",
        "second_weight_entry",
        "manual_weight_entry",
        "mechanical_test",
        "test_certificate",
        "dietool_production",
        "material_indent",
        "material_request",
        "purchase_order",
        "create_dross_entry",
    }

    excluded_models = {
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
        "party",
        "workorderdetail",
        "quotationdetail",
        "keypersons",
        "bankdetails",
        "bankingdetails",
        "billingperson",
        "contactperson",
        "shipingperson",
        "diequotationdetails",
        "proformadetails",
        "gsttype",
        "userprofile",
        "inquirydetail",
        "inquiryquotationdetail",
        "inquirysalesorderdetail",
    }

    all_permissions = (
        Permission.objects.select_related("content_type")
        .filter(content_type__app_label__in=project_apps)
        .exclude(content_type__model__in=excluded_models)
    )

    all_permissions_dict = defaultdict(set)
    for perm in all_permissions:
        all_permissions_dict[perm.content_type.app_label].add(perm.codename)

    # Get user's own and group permissions
    user_permissions = Permission.objects.filter(user=user)
    custom_group_permissions = Permission.objects.filter(
        group__user=user,
        content_type__model__in=[
            ct.model
            for ct in perm.content_type._meta.model.objects.all()
            if ct.model.lower() not in excluded_models
        ],
    )

    # Merge user + group permission strings
    user_permissions_set = {
        f"{perm.content_type.app_label}|{perm.codename}" for perm in user_permissions
    } | {
        f"{perm.content_type.app_label}|{perm.codename}"
        for perm in custom_group_permissions
    }

    # User's role (first group name)
    groups = Group.objects.filter(user=user).values_list("name", flat=True)
    role_name = groups.first() if groups else "unknown"

    # Prepare final response
    permissions_response = {}
    for app_label, actions in all_permissions_dict.items():
        user_actions = [
            action
            for action in actions
            if f"{app_label}|{action}" in user_permissions_set
        ]
        permissions_response[app_label] = user_actions

    return {"role": role_name, "permissions": permissions_response}


def get_user_groups(user):
    groups = Group.objects.filter(user=user)
    group_data = [{"id": group.id, "name": group.name} for group in groups]  # type: ignore
    return group_data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        login_value = attrs.get(
            "email"
        )  # You're using 'email' to send either email or username
        if not login_value:
            raise AuthenticationFailed(
                {
                    "success": False,
                    "message": "Email or username is required",
                }
            )

        # login_value = login_value.strip().lower()  # Normalize input

        keep_me_logged = self.context["request"].data.get("keep_me_logged_in", False)

        # Determine if the input is an email or a username
        if "@" in login_value and "." in login_value:
            user = User.objects.filter(email=login_value).first()
        else:
            user = User.objects.filter(username=login_value).first()

        if user is None:
            raise AuthenticationFailed(
                {
                    "success": False,
                    "message": "No active account found with the given credentials",
                }
            )

        attrs["email"] = user.email
        token: dict = super(CustomTokenObtainPairSerializer, self).validate(attrs)

        group_data = get_user_groups(user)

        permissions = get_user_permissions(user)
        token.update(
            {
                "userData": {
                    "user_id": user.id,  # type: ignore
                    "email": user.email,
                    "first_name": user.first_name,
                    "username": user.username,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "role": group_data,
                    "keep_me_logged_in": keep_me_logged,
                    "last_login": user.last_login,
                    "permissions": permissions,
                    "profile_image": user.profile_image if user.profile_image else "",
                }
            }
        )
        if keep_me_logged:
            access_token = AccessToken(token["access"])
            refresh_token = RefreshToken(token["refresh"])

            # Set custom lifetime
            access_token.set_exp(lifetime=timedelta(days=365))
            refresh_token.set_exp(lifetime=timedelta(days=365))

            token["access"] = str(access_token)
            token["refresh"] = str(refresh_token)

        user.keep_me_logged_in = keep_me_logged
        user.last_login = now()
        user.save()

        log_user_activity(
            user=user,
            action="LOGIN",
            module_name="User",
            description=f"Loggined in {user.first_name}",
            request=self.context["request"],
            payload=dict(self.context["request"].data),
        )

        data = {
            "success": True,
            "message": "Login Successful",
            "data": token,
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def get_auth_token(self, user):
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)
        return token


class TokenRefreshView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            # Extract the refresh token from the request data
            refresh_token = request.data.get("refresh_token")

            # Create a RefreshToken instance using the provided refresh token
            token = RefreshToken(refresh_token)

            # Check if the provided refresh token is valid
            if not token.check_blacklist():
                # Create a new access token
                access_token = token.access_token

                return Response({"access_token": str(access_token)}, status=200)
            else:
                return Response({"detail": "Invalid refresh token"}, status=401)
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=401)
