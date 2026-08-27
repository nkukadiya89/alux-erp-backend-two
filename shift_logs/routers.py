from rest_framework import routers

from .views import ShiftLogViewSet

shiftlog_router = routers.DefaultRouter()

shiftlog_router.register("production-shift-log", ShiftLogViewSet, basename="shift-logs")
