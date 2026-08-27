from rest_framework.routers import DefaultRouter
from mechanical_test.views import MechanicalTestDetailViewSet, MechanicalTestViewSet

mechanical_test_routers = DefaultRouter()

mechanical_test_routers.register(
    "mechanical-test", MechanicalTestViewSet, basename="mechanical_test"
)
mechanical_test_routers.register(
    "mechanical-test-item", MechanicalTestDetailViewSet, basename="mechanical_test_item"
)
