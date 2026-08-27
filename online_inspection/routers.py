from rest_framework.routers import DefaultRouter
from online_inspection.views import OnlineInspectionViewSet

router = DefaultRouter()
router.register(
    r"online-inspection", OnlineInspectionViewSet, basename="online-inspection"
)

urlpatterns = router.urls
