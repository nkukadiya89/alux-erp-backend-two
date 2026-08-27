from rest_framework.routers import DefaultRouter

from msg_logger.views import LogActivityViewSet

activity_log_routers = DefaultRouter()

activity_log_routers.register(
    "activity-log", viewset=LogActivityViewSet, basename="nalco"
)
