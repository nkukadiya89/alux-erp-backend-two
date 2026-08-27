from rest_framework.routers import DefaultRouter

from proforma.views import ProformaViewSet

proforma_routers = DefaultRouter()

proforma_routers.register("proforma", viewset=ProformaViewSet, basename="proforma")
