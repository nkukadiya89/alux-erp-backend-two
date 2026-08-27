from rest_framework.routers import DefaultRouter
from quotation.quotation_views import QuotationDetailViewSet, QuotationViewSet

quotation_routers = DefaultRouter()
quotation_routers.register("quotation", viewset=QuotationViewSet, basename="quotation")
quotation_routers.register(
    "quotation-detail", viewset=QuotationDetailViewSet, basename="quotation-detail"
)
