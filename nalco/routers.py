from rest_framework.routers import DefaultRouter

from nalco.views import NalcoMasterViewSet

nalco_routers = DefaultRouter()
nalco_routers.register("nalco", viewset=NalcoMasterViewSet, basename="nalco")
