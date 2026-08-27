from rest_framework.routers import DefaultRouter
from .views import RecoveryStandardMasterViewSet

recovery_standard_master = DefaultRouter()

recovery_standard_master.register(r"recovery_standard_master", RecoveryStandardMasterViewSet, basename="RSM")