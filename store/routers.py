from rest_framework.routers import DefaultRouter

from .views import StoreArchiveViewSet, StoreViewSet

store_routers = DefaultRouter()

store_routers.register(
    "store",
    viewset=StoreViewSet,
    basename="store",
)
store_routers.register(
    "store-archive",
    viewset=StoreArchiveViewSet,
    basename="store_archive",
)
