from rest_framework.routers import DefaultRouter

from .views import VehicleMasterViewSet

vehiclemaster_routers = DefaultRouter()

vehiclemaster_routers.register(
    "vehiclemaster", viewset=VehicleMasterViewSet, basename="vehiclemaster"
)
