from rest_framework.routers import DefaultRouter

from .views import FirstWeightEntryViewSet

first_weight_entry_routers = DefaultRouter()

first_weight_entry_routers.register(
    "first-weight-entry", viewset=FirstWeightEntryViewSet, basename="first-weight-entry"
)
