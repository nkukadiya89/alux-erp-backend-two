from rest_framework.routers import DefaultRouter

from inquiry.views import InquiryDetailViewSet, InquiryViewSet

inquiry_routers = DefaultRouter()
inquiry_routers.register("enquiry", viewset=InquiryViewSet, basename="enquiry")
inquiry_routers.register(
    "enquiry-details", viewset=InquiryDetailViewSet, basename="enquiry-detail"
)
