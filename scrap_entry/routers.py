from rest_framework.routers import DefaultRouter

from .views import (
    ScrapEntryArchiveViewSet,
    ScrapEntryViewSet,
    ScrapTypeArchiveViewSet,
    ScrapTypeViewSet,
    ProcessArchiveViewSet,
    ProcessViewSet,
)

scrap_entry_routers = DefaultRouter()

# Register archived first so /archived/ is not matched as pk
scrap_entry_routers.register(
    "scrap-entries/archived",
    ScrapEntryArchiveViewSet,
    basename="scrap-entry-archived",
)
scrap_entry_routers.register(
    "scrap-entries",
    ScrapEntryViewSet,
    basename="scrap-entry",
)
scrap_entry_routers.register(
    "scrap-types/archived",
    ScrapTypeArchiveViewSet,
    basename="scrap-type-archived",
)
scrap_entry_routers.register(
    "scrap-types",
    ScrapTypeViewSet,
    basename="scrap-type",
)
scrap_entry_routers.register(
    "processes/archived",
    ProcessArchiveViewSet,
    basename="process-archived",
)
scrap_entry_routers.register(
    "processes",
    ProcessViewSet,
    basename="process",
)
