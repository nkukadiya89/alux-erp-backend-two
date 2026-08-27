from rest_framework.routers import DefaultRouter

from current_stock.views import CurrentStockViewSet

current_stock_routers = DefaultRouter()

current_stock_routers.register(
    "current-stock", viewset=CurrentStockViewSet, basename="current_stock"
)
