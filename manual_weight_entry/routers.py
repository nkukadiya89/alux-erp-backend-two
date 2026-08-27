from rest_framework.routers import DefaultRouter

from .views import ManualWeightEntryViewSet

manual_weight_entry_routers = DefaultRouter()

manual_weight_entry_routers.register(
    "manual-weight-entry",
    viewset=ManualWeightEntryViewSet,
    basename="manual-weight-entry",
)
