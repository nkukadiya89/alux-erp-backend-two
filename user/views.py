import json
import logging
import threading

from django.contrib.auth import logout
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import get_authorization_header
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from email_utils.send_success_mail import send_confirm_mail
from user.models import CustomGroup, User
from user.serializers import UserRegistrationSerializer
from user.user_serializer import UserSerializer
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination
from utils.send_mail import send_mail, send_welcome_mail

logger = logging.getLogger("file")


class UserRegistrationViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    serializer_class = UserRegistrationSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            super().create(request, *args, **kwargs)
            return Response(
                {"message": "User created successfully"}, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return custom_exception(e)


class LogoutViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            authorization_header = get_authorization_header(request).decode("utf-8")
            access_token = authorization_header.split(" ")[1]
            try:
                OutstandingToken.objects.create(token=access_token)
            except Exception as e:
                return custom_exception(e)

            logout(request)
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Logout failed"}, status=status.HTTP_400_BAD_REQUEST
            )


class UserViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]

    search_fields = [
        "id",
        "first_name",
        "last_name",
        "email",
        "status",
        "username",
        "phone",
        "profile_image",
        "deleted",
        "is_active",
        "keep_me_logged_in",
        "otp",
        "whatsapp_otp",
        "created_at",
        "updated_at",
        "last_login",
    ]
    ordering_fields = [
        "id",
        "first_name",
        "last_name",
        "email",
        "status",
        "username",
        "phone",
        "profile_image",
        "deleted",
        "is_active",
        "keep_me_logged_in",
        "otp",
        "whatsapp_otp",
        "created_at",
        "updated_at",
        "last_login",
    ]

    def get_queryset(self):
        queryset = User.objects.all()

        superuser_param = self.request.query_params.get("superuser", "false").lower()
        if superuser_param in ["false", "0", "no"]:
            queryset = queryset.exclude(is_superuser=True)

        id = self.request.query_params.get("id")
        deleted = self.request.query_params.get("deleted", False)

        filters = {}
        if id:
            filters["id"] = id
        if deleted in ["true", "1"]:
            filters["deleted"] = 1
        elif deleted in ["false", "0"]:
            filters["deleted"] = 0

        return queryset.filter(**filters)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            fields_param = request.query_params.get("fields")
            if fields_param and fields_param.strip():
                requested_fields = [
                    f.strip() for f in fields_param.split(",") if f.strip()
                ]
                valid_fields = []

                for field in requested_fields:
                    try:
                        queryset.values(field)
                        valid_fields.append(field)
                    except Exception:
                        continue

                if valid_fields:
                    queryset = queryset.values(*valid_fields)
                    page = self.paginate_queryset(queryset)
                    if page is not None:
                        return self.get_paginated_response(
                            {"success": True, "data": list(page)}
                        )
                    return Response(
                        {"success": True, "data": list(queryset)},
                        status=status.HTTP_200_OK,
                    )

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return custom_exception(e)

    def send_email_user_activate(self, user, context):
        if user:
            send_mail(
                "ALUX-Erp Security Alert For User Activate",
                "reset-pass.html",
                context,
            )

    def send_email_user_inactivate(self, user, context):
        if user:
            send_mail(
                "ALUX-Erp Security Alert For User Deactivate",
                "deactivate-user.html",
                context,
            )

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data

            profile_image = data.get("profile_image")
            form_data = data.get("form_data")

            try:
                if profile_image and not form_data:
                    user = User.objects.get(id=request.user.id)
                    user.created_by = request.user

                    user.upload_profile_image(profile_image)
                    user.save()
                    logger.info(
                        f"Profile photo uploaded successfully for user ID: {user.id}"
                    )
                    return Response(
                        {
                            "success": True,
                            "message": "Profile photo uploaded successfully",
                        },
                        status=status.HTTP_201_CREATED,
                    )

                if form_data:
                    form_data = json.loads(form_data)
                    user = User.objects.filter(
                        email=form_data.get("email"), deleted=0
                    ).first()
                    if user:
                        logger.warning(
                            f"User  with email {form_data.get('email')} already exists."
                        )
                        return Response(
                            {
                                "success": False,
                                "message": "User with this email already exists",
                            }
                        )

                    groups_data = form_data.get("groups", [])
                    for group_name in groups_data:
                        group, created = CustomGroup.objects.get_or_create(
                            name=group_name
                        )
                        if created:
                            logger.info(f"Group '{group_name}' created.")

                    serializer = self.get_serializer(data=form_data)
                    form_data["created_at"] = timezone.now()
                    serializer.is_valid(raise_exception=True)
                    user = serializer.save(created_by=request.user)

                    if profile_image:
                        user.upload_profile_image(profile_image)
                        user.save()

                    email_data = {
                        "name": user.first_name,
                        "email": user.email,
                    }
                    subject = "Welcome to ALUX!"
                    template = "welcome-mail.html"

                    try:
                        send_welcome_mail(subject, template, email_data)
                        logger.info(f"Welcome email sent successfully to: {user.email}")
                    except Exception as email_error:
                        logger.error(
                            f"Failed to send welcome email to {user.email}: {str(email_error)}"
                        )

                    logger.info(f"User  created successfully: {user.email}")

                    payload = clean_payload(request.data)

                    log_user_activity(
                        user=request.user,
                        action="CREATE",
                        module_name="User",
                        description=f"Created user {user.first_name}",
                        request=request,
                        payload=payload,
                    )

                    return Response(
                        {
                            "success": True,
                            "message": "User created successfully",
                            "data": serializer.data,
                        },
                        status=status.HTTP_201_CREATED,
                    )

            except Exception as e:
                logger.error(f"Operation failed: {str(e)}")
                return Response(
                    {"success": False, "message": f"Operation failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            form_data = data.get("form_data")
            profile_image = data.get("profile_image")
            user_id = kwargs.get("pk")

            try:
                user = User.objects.get(id=user_id, deleted=0)

                if not user:
                    return Response(
                        {"success": False, "message": "User not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                if profile_image and not form_data:
                    user.updated_by = request.user
                    user.updated_at = timezone.now()
                    user.upload_profile_image(profile_image)
                    user.save()
                    return Response(
                        {
                            "success": True,
                            "message": "Profile photo updated successfully",
                        },
                        status=status.HTTP_200_OK,
                    )

                if form_data:
                    form_data = json.loads(form_data)
                    serializer = self.get_serializer(user, data=form_data, partial=True)
                    serializer.is_valid(raise_exception=True)
                    user.updated_by = request.user
                    serializer.save(updated_at=timezone.now())

                    if profile_image:
                        user.upload_profile_image(profile_image)
                        user.save()

                    payload = clean_payload(request.data)

                    log_user_activity(
                        user=request.user,
                        action="UPDATE",
                        module_name="User",
                        description=f"Updated user {user.first_name}",
                        request=request,
                        payload=payload,
                    )

                    return Response(
                        {
                            "success": True,
                            "message": "User updated successfully",
                            "data": serializer.data,
                        },
                        status=status.HTTP_200_OK,
                    )

                return Response(
                    {"success": False, "message": "No valid data provided for update"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            except User.DoesNotExist:
                return Response(
                    {"success": False, "message": "User not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            except Exception as e:
                return Response(
                    {"success": False, "message": f"Operation failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

    def perform_destroy(self, instance):

        if instance.deleted == 1 or self.queryset is None:
            raise ValidationError({"error": "User is already deleted."})

        instance.deleted = 1
        instance.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(
                {"success": "User deleted successfully."}, status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["patch"], url_path="user-status-change")
    def user_status_change(self, request, pk=None):

        try:
            user_id = request.data.get("id")
            user = self.get_queryset().get(id=user_id)
        except ObjectDoesNotExist:
            return Response(
                {"message": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get("status")

        if new_status == "active":
            if user.status == "active":
                return Response(
                    {"message": "User is already active."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.status = "active"
            user.is_active = True
            user.save()

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="User",
                description=f"Activated user {user.first_name}",
                request=request,
                payload=payload,
            )

            context = {"name": user.first_name, "email": user.email}

            email_thread = threading.Thread(
                target=self.send_email_user_activate,
                args=(user, context),
            )
            email_thread.start()

            return Response(
                {"message": "User activated successfully."}, status=status.HTTP_200_OK
            )

        elif new_status == "inactive":
            if user.status == "inactive":
                return Response(
                    {"message": "User is already inactive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.status = "inactive"
            user.is_active = False
            user.save()

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="User",
                description=f"Deactivated user {user.first_name}",
                request=request,
                payload=payload,
            )

            context = {"name": user.first_name, "email": user.email}

            email_thread = threading.Thread(
                target=self.send_email_user_inactivate,
                args=(user, context),
            )
            email_thread.start()

            return Response(
                {"message": "User deactivated successfully."}, status=status.HTTP_200_OK
            )

        elif new_status == "pending":
            if user.status == "pending":
                return Response(
                    {"message": "User is already pending."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.status = "pending"
            user.is_active = False
            user.save()

            return Response(
                {"message": "User status set to pending successfully."},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {
                    "message": "Invalid status value. Expected 'active', 'inactive', or 'pending'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class ChangePasswordViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all().order_by("-id")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not new_password or not confirm_password:
            return Response(
                {"success": False, "message": "All fields are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"success": False, "message": "New passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(id=user_id).first()

        user.set_password(new_password)
        user.save()

        payload = clean_payload(request.data)

        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="User",
            description=f"Updated password for user {user.first_name}",
            request=request,
            payload=payload,
        )

        context = {"name": user.first_name, "email": user.email}
        send_confirm_mail(
            "ALUX-Erp Password Change Notification",
            "password-changed-confirmation.html",
            context,
        )

        return Response(
            {"success": True, "message": "Password successfully changed"},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(
        detail=False,
        methods=["POST"],
        url_path="change-password",
        permission_classes=[AllowAny],
    )
    def user_password_change(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not current_password or not new_password or not confirm_password:
            return Response(
                {"success": False, "message": "All fields are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"success": False, "message": "New passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(id=user_id).first()

        if not user.check_password(current_password):
            return Response(
                {"success": False, "message": "Old password is incorrect"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.set_password(new_password)
        user.save()

        payload = clean_payload(request.data)

        log_user_activity(
            user=user,
            action="UPDATE",
            module_name="User",
            description=f"Updated password for user {user.first_name}",
            request=request,
            payload=payload,
        )

        return Response(
            {"success": True, "message": "Password successfully changed"},
            status=status.HTTP_200_OK,
        )
