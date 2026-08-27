from rest_framework import routers

from .views import ShiftMasterViewSet

shift_router = routers.DefaultRouter()

shift_router.register("shift-master", ShiftMasterViewSet, basename="shift-master")
