from rest_framework.routers import DefaultRouter

from product.alloy_views import AlloyArchiveViewSet, AlloyViewSet
from product.item_views import (
    ItemArchiveViewSet,
    ItemTypeViewSet,
    ItemViewSet,
    MaterialCenterViewSet,
    ValuationMethodViewSet,
)
from product.standard_views import StandardMasterViewSet
from product.temper_views import TemperArchiveViewSet, TemperViewSet

product_routers = DefaultRouter()

product_routers.register("alloy", viewset=AlloyViewSet, basename="alloy")
product_routers.register(
    "standard", viewset=StandardMasterViewSet, basename="standard_master"
)
product_routers.register(
    "alloy-archive", viewset=AlloyArchiveViewSet, basename="alloy_archive"
)
product_routers.register("temper", viewset=TemperViewSet, basename="temper")
product_routers.register(
    "temper-archive", viewset=TemperArchiveViewSet, basename="temper_archive"
)
product_routers.register("item", viewset=ItemViewSet, basename="item")
product_routers.register(
    "item-archive", viewset=ItemArchiveViewSet, basename="item-archive"
)
product_routers.register("item-types", ItemTypeViewSet, basename="item_type")
product_routers.register(
    "valuation-method", ValuationMethodViewSet, basename="valuation_method"
)
product_routers.register(
    "material-center", MaterialCenterViewSet, basename="material_center"
)
