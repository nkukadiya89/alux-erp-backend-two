from rest_framework.routers import DefaultRouter

from bundle_verification.views import (
    DispatchVerificationViewSet,
    StockVerificationViewSet,
)

bundle_verification_routers = DefaultRouter()

bundle_verification_routers.register(
    "stock-verification",
    viewset=StockVerificationViewSet,
    basename="stock_verification",
)
bundle_verification_routers.register(
    "dispatch-verification",
    viewset=DispatchVerificationViewSet,
    basename="dispatch_verification",
)
