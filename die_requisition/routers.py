from rest_framework.routers import DefaultRouter

from .views import DieRequisitionDetailViewSet, DieRequisitionViewSet

die_requisition_router = DefaultRouter()

die_requisition_router.register(
    r"die-requisition", DieRequisitionViewSet, basename="die-requisition"
)
die_requisition_router.register(
    r"die-requisition-details",
    DieRequisitionDetailViewSet,
    basename="die-requisition-detail",
)
