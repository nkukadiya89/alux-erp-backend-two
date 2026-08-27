from rest_framework.routers import DefaultRouter

from bundle_outward.views import BundleOutwardViewSet

bundle_outward_routers = DefaultRouter()

bundle_outward_routers.register(
    "bundle-outward", viewset=BundleOutwardViewSet, basename="bundle_outward"
)
