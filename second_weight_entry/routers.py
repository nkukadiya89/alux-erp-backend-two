from rest_framework.routers import DefaultRouter

from .views import SecondWeightEntryViewSet

second_weight_entry_routers = DefaultRouter()

second_weight_entry_routers.register(
    "second-weight-entry",
    viewset=SecondWeightEntryViewSet,
    basename="second-weight-entry",
)
