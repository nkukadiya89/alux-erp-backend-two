from rest_framework.routers import DefaultRouter

from warehouse.current_stock import WarehouseCurrentStockViewSet
from warehouse.views import WarehouseViewSet

warehouse_routers = DefaultRouter()

warehouse_routers.register("warehouse", viewset=WarehouseViewSet, basename="warehouse")
warehouse_routers.register(
    "warehouse-current-stock",
    viewset=WarehouseCurrentStockViewSet,
    basename="warehouse-current-stock",
)
