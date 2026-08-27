from rest_framework.routers import DefaultRouter

from .views import ProductionViewSet

production_routers = DefaultRouter()
production_routers.register("production", ProductionViewSet, basename="production")
