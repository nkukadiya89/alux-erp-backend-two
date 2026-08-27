from rest_framework.routers import DefaultRouter
from .views import ReturnToVendorViewSet

rtv_router = DefaultRouter()

rtv_router.register(r"return-to-vendor", ReturnToVendorViewSet, basename="return-to-vendor") 