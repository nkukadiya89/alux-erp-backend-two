from rest_framework.routers import DefaultRouter
from .views import VehicleTypeViewSet

vehicletype_routers = DefaultRouter()
vehicletype_routers.register(
    "vehicletype", viewset=VehicleTypeViewSet, basename="vehicletype"
)
