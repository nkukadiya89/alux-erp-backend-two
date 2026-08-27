from rest_framework import routers
from dimension_inspection.views import (
    DimensionInspectionViewSet,
    DimensionInspectionDetailViewSet,
)

dimension_inspection_routers = routers.DefaultRouter()
dimension_inspection_routers.register(
    r"dimension-inspection", DimensionInspectionViewSet, basename="dimension-inspection"
)
dimension_inspection_routers.register(
    r"dimension-inspection-item",
    DimensionInspectionDetailViewSet,
    basename="dimension-inspection-detail",
)
