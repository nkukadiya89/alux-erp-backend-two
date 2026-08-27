from rest_framework.routers import DefaultRouter

from party.party_views import PartyViewSet

party_routers = DefaultRouter()

party_routers.register("party", viewset=PartyViewSet, basename="party")
