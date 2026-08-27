from rest_framework.routers import DefaultRouter

from bundle_inward.views import BundleInwardViewSet
from bundle_inward.excess_stock_views import ExcessStockViewSet

bundle_inward_routers = DefaultRouter()

bundle_inward_routers.register(
    "bundle-inward", viewset=BundleInwardViewSet, basename="bundle_inward"
)
bundle_inward_routers.register(
    "excess-stock", viewset=ExcessStockViewSet, basename="excess_stock"
)
