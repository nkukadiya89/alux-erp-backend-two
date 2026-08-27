from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ScrapTransferArchiveViewSet,
    ScrapTransferViewSet,
    ScrapStoreDropdownView,
    ScrapItemsAvailableInStoreView,
)

scrap_transfer_routers = DefaultRouter()

# Register archived first so /archived/ is not matched as pk
scrap_transfer_routers.register(
    "scrap-transfers/archived",
    ScrapTransferArchiveViewSet,
    basename="scrap-transfer-archived",
)
scrap_transfer_routers.register(
    "scrap-transfers",
    ScrapTransferViewSet,
    basename="scrap-transfer",
)

# Extra URL for scrap items available in store (query param store_id)
# GET /api/v1/scrap-transfers/scrap-items/available-in-store/?store_id=
scrap_transfer_extra_urlpatterns = [
    path(
        "scrap-transfers/scrap-items/available-in-store/",
        ScrapItemsAvailableInStoreView.as_view(),
        name="scrap-items-available-in-store",
    ),
    # GET /api/v1/stores/scrap-store-dropdown/
    path(
        "stores/scrap-store-dropdown/",
        ScrapStoreDropdownView.as_view(),
        name="scrap-store-dropdown",
    ),
]
