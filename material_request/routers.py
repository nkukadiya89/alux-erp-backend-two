from rest_framework.routers import DefaultRouter
from .views import MaterialRequestViewSet, MaterialRequestDetailViewSet


material_request_router = DefaultRouter()

material_request_router.register(r"material-request", MaterialRequestViewSet, basename="material-request")
material_request_router.register(r"material-request-detail", MaterialRequestDetailViewSet, basename="request-item")

