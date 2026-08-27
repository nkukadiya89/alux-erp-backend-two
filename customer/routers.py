from rest_framework.routers import DefaultRouter
from customer.customer_master_views import CustomerTypeViewSet
from customer.customer_views import (
    BankingDetailViewSet,
    CustomerViewSet,
)
from imports.customer_type import CustomerTypeBulkImportAPIView, CustomerTypeSampleDownloadAPIView
from django.urls import path, include

customer_routers = DefaultRouter()

customer_routers.register("customer", viewset=CustomerViewSet, basename="customer")
customer_routers.register(
    "customer-types", viewset=CustomerTypeViewSet, basename="customer_customertype"
)
customer_routers.register(
    "customer-bankingdetails",
    viewset=BankingDetailViewSet,
    basename="customer_BankingDetails",
)
customertype_urlpatterns = [
    path("", include(customer_routers.urls)),
    path(
        "customer-type-import/",
        CustomerTypeBulkImportAPIView.as_view(),
        name="customer_import",
    ),
    path(
        "customer-type-export/",
        CustomerTypeSampleDownloadAPIView.as_view(),
        name="customer_export",
    )
]