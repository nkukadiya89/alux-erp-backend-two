from rest_framework.routers import DefaultRouter

from vendor.views import VendorViewSet

vendor_routers = DefaultRouter()

vendor_routers.register("vendor", viewset=VendorViewSet, basename="vendor")
