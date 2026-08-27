from rest_framework.routers import DefaultRouter

from planning.views import PlanningViewSet, ApprovedPlanningViewSet

planning_routers = DefaultRouter()

planning_routers.register("planning", viewset=PlanningViewSet, basename="planning")
planning_routers.register(
    "approved-planning", viewset=ApprovedPlanningViewSet, basename="approved-planning"
)
