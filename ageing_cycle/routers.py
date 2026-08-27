from rest_framework.routers import DefaultRouter
from ageing_cycle.views import AgingCycleViewSet

ageing_cycle_routers = DefaultRouter()  

ageing_cycle_routers.register("ageing-cycle", AgingCycleViewSet, basename="ageing_cycle")