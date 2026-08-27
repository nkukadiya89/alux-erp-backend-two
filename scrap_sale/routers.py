from rest_framework.routers import DefaultRouter

from .views import (
    ScrapSaleArchiveViewSet,
    ScrapSaleViewSet,
    ScrapItemViewSet,
)

scrap_sale_routers = DefaultRouter()

# Register more specific path first so /archived/ is not matched as pk
scrap_sale_routers.register(
    "scrap-sales/archived",
    ScrapSaleArchiveViewSet,
    basename="scrap-sale-archived",
)
scrap_sale_routers.register(
    "scrap-sales",
    ScrapSaleViewSet,
    basename="scrap-sale",
)
scrap_sale_routers.register(
    "scrap-items",
    ScrapItemViewSet,
    basename="scrap-item",
)
