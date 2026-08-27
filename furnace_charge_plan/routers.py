from rest_framework import routers

from .views import (
    FurnaceChargePlanViewSet,
    FurnaceChargePlanDetailViewSet
)

furnace_charge_plan_router = routers.DefaultRouter()

furnace_charge_plan_router.register(r"furnace-charge-plan",FurnaceChargePlanViewSet, basename="furnace-charge-plan")
furnace_charge_plan_router.register(r"furnace-charge-plan-detail", FurnaceChargePlanDetailViewSet, basename="furnace-charge-plan-detail")