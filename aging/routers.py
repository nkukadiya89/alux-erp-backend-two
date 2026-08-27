from rest_framework.routers import DefaultRouter
from aging.views import (
    AgeingBatchViewSet,
    AgeingBatchDetailViewSet,
    AgeingTemperatureLogViewSet,
)

aging_routers = DefaultRouter()

aging_routers.register("ageing-batch", AgeingBatchViewSet, basename="ageing_batch")
aging_routers.register(
    "ageing-batch-detail", AgeingBatchDetailViewSet, basename="ageing_batch_detail"
)
aging_routers.register(
    "ageing-temperature-log",
    AgeingTemperatureLogViewSet,
    basename="ageing_temperature_log",
)
