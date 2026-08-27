from rest_framework.routers import DefaultRouter
from .views import QualityInspectionViewSet

quality_inspection_router = DefaultRouter()

quality_inspection_router.register(r'quality-inspection', QualityInspectionViewSet, basename='quality-inspection')