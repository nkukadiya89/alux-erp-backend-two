from django.urls import path
from rest_framework.routers import DefaultRouter

from settings.views import (
    AllSettingsAPIView,
    CompanySettingsViewSet,
    FinancialSettingsViewSet,
    NotificationSettingsViewSet,
    TaxComplianceSettingsViewSet,
    TermAndConditionSettingsViewSet,
    ProductionSettingsViewSet,
)

settings_routers = DefaultRouter()

settings_routers.register(
    r"company-settings", CompanySettingsViewSet, basename="company-settings"
)
settings_routers.register(
    r"notification-settings",
    NotificationSettingsViewSet,
    basename="notification-settings",
)
settings_routers.register(
    r"tax-compliance-settings",
    TaxComplianceSettingsViewSet,
    basename="tax-compliance-settings",
)
settings_routers.register(
    r"financial-settings", FinancialSettingsViewSet, basename="financial-settings"
)
settings_routers.register(
    r"terms-and-conditions",
    TermAndConditionSettingsViewSet,
    basename="terms-and-conditions",
)
settings_routers.register(
    r"production-settings", ProductionSettingsViewSet, basename="production-settings"
)
settings_extra_urls = [
    path("settings/", AllSettingsAPIView.as_view(), name="all-settings"),
]
