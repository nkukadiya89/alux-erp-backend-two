from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    GateEntryArchiveViewSet,
    GateEntryViewSet,
)

gate_entry_routers = DefaultRouter()

gate_entry_routers.register(
    "gate-entries",
    GateEntryViewSet,
    basename="gate-entry",
)
gate_entry_routers.register(
    "gate-entries/archived",
    GateEntryArchiveViewSet,
    basename="gate-entry-archived",
)

gate_entry_extra_urlpatterns = []
