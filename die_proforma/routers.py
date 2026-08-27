from rest_framework.routers import DefaultRouter

from die_proforma.views import DieProformaViewSet

die_proforma_router = DefaultRouter()

die_proforma_router.register("die-proforma", viewset=DieProformaViewSet, basename="die-proforma")
