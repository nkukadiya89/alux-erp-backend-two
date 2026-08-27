from rest_framework.routers import DefaultRouter

from .views import TransporterViewSet

transporter_routers = DefaultRouter()

transporter_routers.register(
    "transporter", viewset=TransporterViewSet, basename="transporter"
)
