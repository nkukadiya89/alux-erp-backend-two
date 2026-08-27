from rest_framework.routers import DefaultRouter
from common.department_views import DepartmentArchiveViewSet, DepartmentViewSet
from common.views import FinancialYearViewSet
from common.views import StoreTypeViewSet
from common.views import GstTypeViewSet
from common.item_category_views import ItemCategoryArchiveViewSet, ItemCategoryViewSet
from common.views import JobWorkTypeViewSet
from common.model_list_views import ContentTypeListView
from common.views import PackingModeViewSet
from common.plant_capability_views import PlantCapabilityViewSet
from common.plant_type_capability_views import PlantTypeCapabilityViewSet
from common.plant_type_views import PlantTypeArchiveViewSet, PlantTypeViewSet

from common.plant_views import PlantArchiveViewSet, PlantViewSet
from common.views import SectionTypeViewSet
from common.views import UOMViewSet
from common.views import YieldUnitViewSet
from django.urls import path, include
from imports.packing_mode import PackingModeBulkImportAPIView

common_routers = DefaultRouter()

common_routers.register("gst-type", viewset=GstTypeViewSet, basename="gst_type")
common_routers.register(
    "job-work", viewset=JobWorkTypeViewSet, basename="job_work_type"
)
common_routers.register(
    "model-list", viewset=ContentTypeListView, basename="model_list"
)
common_routers.register(
    "financial-year", viewset=FinancialYearViewSet, basename="financial_year"
)
common_routers.register(
    "packing-mode", viewset=PackingModeViewSet, basename="packing_mode"
)
common_routers.register("plants", viewset=PlantViewSet, basename="plant")
common_routers.register(
    "plants-archive", viewset=PlantArchiveViewSet, basename="plant-archive"
)

common_routers.register("plant-types", viewset=PlantTypeViewSet, basename="plant-type")
common_routers.register(
    "plant-types-archive",
    viewset=PlantTypeArchiveViewSet,
    basename="plant-type-archive",
)
common_routers.register(
    "plant-capabilities", viewset=PlantCapabilityViewSet, basename="plant-capability"
)
common_routers.register(
    "plant-type-capabilities",
    viewset=PlantTypeCapabilityViewSet,
    basename="plant-type-capability",
)
common_routers.register(
    "section-types", viewset=SectionTypeViewSet, basename="section-type"
)
common_routers.register("departments", viewset=DepartmentViewSet, basename="department")
common_routers.register(
    "departments-archive",
    viewset=DepartmentArchiveViewSet,
    basename="department-archive",
)
common_routers.register(
    "item-categories", viewset=ItemCategoryViewSet, basename="item-category"
)
common_routers.register(
    "item-categories-archive",
    viewset=ItemCategoryArchiveViewSet,
    basename="item-category-archive",
)
common_routers.register("uom", viewset=UOMViewSet, basename="uom")
common_routers.register("yield-unit", viewset=YieldUnitViewSet, basename="yield-unit")
common_routers.register("store-types", viewset=StoreTypeViewSet, basename="store-type")
common_urlpatterns = [
    path("", include(common_routers.urls)),
    path(
        "packing-mode-import/",
        PackingModeBulkImportAPIView.as_view(),
        name="packing_mode_import",
    )
]