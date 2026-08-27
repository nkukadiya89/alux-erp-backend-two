from rest_framework.routers import DefaultRouter

from inquiry_quotation.views import (
    InquiryQuotationDetailViewSet,
    InquiryQuotationViewSet,
)

inquiry_quotation_routers = DefaultRouter()
inquiry_quotation_routers.register(
    "inquiry-quotation", viewset=InquiryQuotationViewSet, basename="inquiry-quotation"
)
inquiry_quotation_routers.register(
    "inquiry-quotation-details",
    viewset=InquiryQuotationDetailViewSet,
    basename="inquiry-quotation-detail",
)
