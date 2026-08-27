from rest_framework.routers import DefaultRouter
from .views import MaterialViewSet

material_routers = DefaultRouter()

material_routers.register(
    "material",
    MaterialViewSet,
    basename="material"
)