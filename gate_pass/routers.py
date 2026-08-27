from rest_framework.routers import DefaultRouter

from .views import GatePassArchiveViewSet, GatePassViewSet

gate_pass_routers = DefaultRouter()

gate_pass_routers.register(
    "gate-passes",
    GatePassViewSet,
    basename="gate-pass",
)

gate_pass_routers.register(
    "gate-passes/archived",
    GatePassArchiveViewSet,
    basename="gate-pass-archived",
)
