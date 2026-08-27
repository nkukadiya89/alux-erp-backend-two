from rest_framework.routers import DefaultRouter

from inquiry_salesorder.views import (
    InquirySalesOrderArchiveViewSet,
    InquirySalesOrderDetailViewSet,
    InquirySalesOrderViewSet,
    InquiryFixedSalesOrderViewSet
)

inquiry_salesorder_routers = DefaultRouter()
inquiry_salesorder_routers.register(
    "inquiry-salesorder",
    viewset=InquirySalesOrderViewSet,
    basename="inquiry-salesorder",
)
inquiry_salesorder_routers.register(
    "inquiry-fixed-salesorder",
    viewset=InquiryFixedSalesOrderViewSet,
    basename="fixed-salesorder"
)
inquiry_salesorder_routers.register(
    "inquiry-salesorder-archive",
    viewset=InquirySalesOrderArchiveViewSet,
    basename="inquiry-salesorder-archive",
)
inquiry_salesorder_routers.register(
    "inquiry-salesorder-detail",
    viewset=InquirySalesOrderDetailViewSet,
    basename="inquiry-salesorder-detail",
)
