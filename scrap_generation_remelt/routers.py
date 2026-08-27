from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    RemeltItemsAvailableInStoreView,
    RemeltStoreDropdownView,
    ScrapGenerationRemeltArchiveViewSet,
    ScrapGenerationRemeltViewSet,
)

scrap_generation_remelt_routers = DefaultRouter()

scrap_generation_remelt_routers.register(
    "scrap-generation-remelts/archived",
    ScrapGenerationRemeltArchiveViewSet,
    basename="scrap-generation-remelt-archived",
)
scrap_generation_remelt_routers.register(
    "scrap-generation-remelts",
    ScrapGenerationRemeltViewSet,
    basename="scrap-generation-remelt",
)

scrap_generation_remelt_extra_urlpatterns = [
    path(
        "scrap-generation-remelts/items/available-in-store/",
        RemeltItemsAvailableInStoreView.as_view(),
        name="scrap-generation-remelt-items-available-in-store",
    ),
    path(
        "stores/remelt-store-dropdown/",
        RemeltStoreDropdownView.as_view(),
        name="remelt-store-dropdown",
    ),
]
