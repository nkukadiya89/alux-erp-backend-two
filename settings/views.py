from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.master_views import BaseModelViewSet
from settings.models import (
    CompanySettings,
    FinancialSettings,
    NotificationSettings,
    TaxComplianceSettings,
    TermAndConditionSettings,
    ProductionSettings
)
from settings.serializers import (
    CompanySettingsSerializer,
    FinancialSettingsSerializer,
    NotificationSettingsSerializer,
    ProductionSettingsListSerializer,
    TaxComplianceSettingsSerializer,
    TermAndConditionSettingsSerializer,
    ProductionSettingsSerializer
)
from utils.error_handling import custom_exception
from utils.pagination import Pagination


class AllSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            company_settings = CompanySettings.objects.filter(deleted=False).first()
            notification_settings = NotificationSettings.objects.filter(
                deleted=False
            ).first()
            tax_compliance_settings = TaxComplianceSettings.objects.first()
            financial_settings = FinancialSettings.objects.filter(deleted=False).first()
            term_and_condition_settings = TermAndConditionSettings.objects.filter(
                deleted=False
            ).first()
            production_settings = ProductionSettings.objects.filter(deleted=False).first()

            data = {
                "company_settings": (
                    CompanySettingsSerializer(company_settings).data
                    if company_settings
                    else None
                ),
                "notification_settings": (
                    NotificationSettingsSerializer(notification_settings).data
                    if notification_settings
                    else None
                ),
                "tax_compliance_settings": (
                    TaxComplianceSettingsSerializer(tax_compliance_settings).data
                    if tax_compliance_settings
                    else None
                ),
                "financial_settings": (
                    FinancialSettingsSerializer(financial_settings).data
                    if financial_settings
                    else None
                ),
                "term_and_condition_settings": (
                    TermAndConditionSettingsSerializer(term_and_condition_settings).data
                    if term_and_condition_settings
                    else None
                ),
                "production_settings": (
                    ProductionSettingsListSerializer(production_settings).data
                    if production_settings
                    else None
                ),
            }

            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            return custom_exception(e)


class CompanySettingsViewSet(BaseModelViewSet, ModelViewSet):
    queryset = CompanySettings.objects.all().order_by("-id")
    serializer_class = CompanySettingsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["company_name", "legal_name", "email", "phone"]
    ordering_fields = ["company_name", "created_at", "updated_at"]
    fy_filtering_enabled = False

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                instance = serializer.save(
                    created_by=request.user, updated_by=request.user
                )

                company_logo = request.FILES.get("company_logo")
                if company_logo:
                    try:
                        instance.upload_doc({"company_logo": company_logo})
                        instance.refresh_from_db()
                    except ValidationError as e:
                        return Response(
                            {
                                "success": False,
                                "message": "File upload failed.",
                                "errors": (
                                    e.message_dict
                                    if hasattr(e, "message_dict")
                                    else str(e)
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Company settings created successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data = request.data.copy()
            serializer = self.get_serializer(instance, data=data, partial=True)
            if serializer.is_valid():
                instance = serializer.save(updated_by=request.user)

                company_logo = request.FILES.get("company_logo")
                if company_logo:
                    try:
                        instance.upload_doc({"company_logo": company_logo})
                        instance.refresh_from_db()
                    except ValidationError as e:
                        return Response(
                            {
                                "success": False,
                                "message": "File upload failed.",
                                "errors": (
                                    e.message_dict
                                    if hasattr(e, "message_dict")
                                    else str(e)
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Company settings updated successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)


class NotificationSettingsViewSet(BaseModelViewSet, ModelViewSet):
    queryset = NotificationSettings.objects.all().order_by("-id")
    serializer_class = NotificationSettingsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["system_email", "smtp_server"]
    ordering_fields = ["created_at", "updated_at"]
    fy_filtering_enabled = False

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                instance = serializer.save(
                    created_by=request.user, updated_by=request.user
                )

                alert_emails = request.data.get("alert_emails", [])
                if alert_emails:
                    instance.alert_emails.set(alert_emails)

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Notification settings created successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                instance = serializer.save(updated_by=request.user)

                if "alert_emails" in request.data:
                    instance.alert_emails.set(request.data.get("alert_emails", []))

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Notification settings updated successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)


class TaxComplianceSettingsViewSet(ModelViewSet):
    queryset = TaxComplianceSettings.objects.all().order_by("-id")
    serializer_class = TaxComplianceSettingsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    search_fields = ["tax_registration_no", "tax_report_email"]
    ordering_fields = ["tax_registration_no"]
    fy_filtering_enabled = False

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        try:
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.get_serializer(queryset, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                instance = serializer.save()

                compliance_document = request.FILES.get("compliance_document")
                if compliance_document:
                    try:
                        instance.upload_doc(
                            {"compliance_document": compliance_document}
                        )
                        instance.refresh_from_db()
                    except ValidationError as e:
                        return Response(
                            {
                                "success": False,
                                "message": "File upload failed.",
                                "errors": (
                                    e.message_dict
                                    if hasattr(e, "message_dict")
                                    else str(e)
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Tax compliance settings created successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data = request.data.copy()
            serializer = self.get_serializer(instance, data=data, partial=True)
            if serializer.is_valid():
                instance = serializer.save()

                compliance_document = request.FILES.get("compliance_document")
                if compliance_document:
                    try:
                        instance.upload_doc(
                            {"compliance_document": compliance_document}
                        )
                        instance.refresh_from_db()
                    except ValidationError as e:
                        return Response(
                            {
                                "success": False,
                                "message": "File upload failed.",
                                "errors": (
                                    e.message_dict
                                    if hasattr(e, "message_dict")
                                    else str(e)
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Tax compliance settings updated successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)


class FinancialSettingsViewSet(ModelViewSet):
    queryset = FinancialSettings.objects.all().order_by("-id")
    serializer_class = FinancialSettingsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["fiscal_year_start", "payment_terms", "invoice_prefix"]
    ordering_fields = ["fiscal_year_start", "created_at", "updated_at"]
    fy_filtering_enabled = False

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                instance = serializer.save(
                    created_by=request.user, updated_by=request.user
                )

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Financial settings created successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                instance = serializer.save(updated_by=request.user)

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Financial settings updated successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)


class TermAndConditionSettingsViewSet(BaseModelViewSet, ModelViewSet):
    queryset = TermAndConditionSettings.objects.all().order_by("-id")
    serializer_class = TermAndConditionSettingsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["id"]
    ordering_fields = ["created_at", "updated_at"]
    fy_filtering_enabled = False

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                instance = serializer.save(
                    created_by=request.user, updated_by=request.user
                )

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Terms and Conditions settings created successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                instance = serializer.save(updated_by=request.user)

                response_serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "Terms and Conditions settings updated successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return custom_exception(e)


class ProductionSettingsViewSet(BaseModelViewSet):
    queryset = ProductionSettings.objects.all().order_by("-id")
    serializer_class = ProductionSettingsSerializer
    list_serializer_class = ProductionSettingsListSerializer
