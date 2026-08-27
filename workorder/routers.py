from rest_framework.routers import DefaultRouter

from workorder.views import OpenWorkOrderViewSet
from workorder.workorder_views import WorkOrderViewSet
from workorder.process_views import WorkOrderProcessTrackingViewSet

workorder_routers = DefaultRouter()

workorder_routers.register("workorder", viewset=WorkOrderViewSet, basename="workorder")
workorder_routers.register(
    "open-workorder", viewset=OpenWorkOrderViewSet, basename="open-workorder"
)
workorder_routers.register(
    "workorder-process-tracking",
    viewset=WorkOrderProcessTrackingViewSet,
    basename="workorder-process-tracking",
)
