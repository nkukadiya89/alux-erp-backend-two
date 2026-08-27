from rest_framework.routers import DefaultRouter

from .archive_views import (
    AdditiveMasterArchiveViewSet,
    FurnaceArchiveViewSet,
    RecoveryStandardArchiveViewSet,
)
from .views import (
    AdditiveCategoryViewSet,
    AdditiveMasterViewSet,
    FuelTypeViewSet,
    FurnaceTypeViewSet,
    FurnaceViewSet,
    MaterialTypeViewSet,
    RecoveryStandardViewSet,
)

melting_furnace_routers = DefaultRouter()
melting_furnace_routers.register(r"furnace", FurnaceViewSet, basename="furnace")
melting_furnace_routers.register(
    r"additive-master", AdditiveMasterViewSet, basename="additive_master"
)
melting_furnace_routers.register(
    r"recovery-standard", RecoveryStandardViewSet, basename="recovery_standard"
)
melting_furnace_routers.register(
    r"furnace-archive", FurnaceArchiveViewSet, basename="furnace_archive"
)
melting_furnace_routers.register(
    r"additive-master-archive",
    AdditiveMasterArchiveViewSet,
    basename="additive_master_archive",
)
melting_furnace_routers.register(
    r"recovery-standard-archive",
    RecoveryStandardArchiveViewSet,
    basename="recovery_standard_archive",
)
melting_furnace_routers.register(
    r"furnace-type", FurnaceTypeViewSet, basename="furnace_type"
)
melting_furnace_routers.register(r"fuel-type", FuelTypeViewSet, basename="fuel_type")
melting_furnace_routers.register(
    r"additive-category", AdditiveCategoryViewSet, basename="additive_category"
)
melting_furnace_routers.register(
    r"material-types", MaterialTypeViewSet, basename="material_type"
)

urlpatterns = melting_furnace_routers.urls
