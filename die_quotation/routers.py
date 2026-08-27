from rest_framework.routers import DefaultRouter

from .views import DieQuotationViewSet

die_quotation_routers = DefaultRouter()

die_quotation_routers.register(
    "die-quotation", DieQuotationViewSet, basename="die_quotation"
)
