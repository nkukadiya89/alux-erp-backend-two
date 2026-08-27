from rest_framework.routers import DefaultRouter
from .views import  PurchaseOrderViewSet, PurchaseOrderDetailViewSet


purchase_order_router = DefaultRouter()


purchase_order_router.register(r"purchase-order", PurchaseOrderViewSet, basename="purchase-order")
purchase_order_router.register(r"purchase-order-item", PurchaseOrderDetailViewSet, basename="purchase-order-item")
