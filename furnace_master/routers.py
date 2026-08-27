from rest_framework.routers import DefaultRouter
from .views import FurnaceMasterViewSet

furnace_master_router = DefaultRouter()

furnace_master_router.register(
    r'furnace-master',
    FurnaceMasterViewSet,
    basename='furnace-master'
)