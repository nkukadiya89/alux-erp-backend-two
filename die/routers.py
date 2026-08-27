from django.urls import path, include
from rest_framework.routers import DefaultRouter
from die.conversion_views import (
    ConversionRateItemsViewSet,
    ConversionRateVersionsViewSet,
    ConversionRateViewSet,
)
from die.die_master_views import (
    DieCategoryViewSet,
    DieGroupViewSet,
    DiePressArchiveViewSet,
    DiePressViewSet,
    DieSizeViewSet,
    DieSubCategoryViewSet,
    DieTypeViewSet,
)
from die.die_views import (
    DeleteDieUploadedFile,
    DieViewSet,
    SectionBalloonDimensionsViewSet,
)
from die.views import DieWithBallonViewSet
from die.dietool_views import DieToolViewSet, GetDieToolDetials
from imports.die_size import DieSizeBulkImportAPIView
from imports.section_group import DieGroupBulkImportAPIView
from imports.section_category import DieCategoryBulkImportAPIView
from imports.section_subcategory import DieSubCategoryBulkImportAPIView
from imports.section_import_view import SectionAsyncImportAPIView, BalloonDimensionAsyncImportAPIView, DieToolAsyncImportAPIView

die_routers = DefaultRouter()

die_routers.register("section", viewset=DieViewSet, basename="section")
die_routers.register("die", viewset=DieWithBallonViewSet, basename="die")
die_routers.register(
    "section-balloon",
    viewset=SectionBalloonDimensionsViewSet,
    basename="section_balloon",
)
die_routers.register(
    "delete-die-files", viewset=DeleteDieUploadedFile, basename="delete_die_files"
)
die_routers.register("die-tool", viewset=DieToolViewSet, basename="die_tool")
die_routers.register(
    "die-category", viewset=DieCategoryViewSet, basename="die_category"
)
die_routers.register("die-group", viewset=DieGroupViewSet, basename="die_group")
die_routers.register("die-size", viewset=DieSizeViewSet, basename="die_size")
die_routers.register("die-type", viewset=DieTypeViewSet, basename="die_type")
die_routers.register(
    "die-subcategory", viewset=DieSubCategoryViewSet, basename="die_subcategory"
)
die_routers.register("die-press", viewset=DiePressViewSet, basename="die_press")
die_routers.register(
    "die-press-archive", viewset=DiePressArchiveViewSet, basename="die_press_archive"
)
die_routers.register(
    "die-tool-details", viewset=GetDieToolDetials, basename="die_tool_details"
)
die_routers.register(
    "conversion-rate", viewset=ConversionRateViewSet, basename="conversion_rate"
)
die_routers.register(
    "conversion-rate-items",
    viewset=ConversionRateItemsViewSet,
    basename="conversion_rate_items",
)
die_routers.register(
    "conversion-rate-versions",
    viewset=ConversionRateVersionsViewSet,
    basename="conversion_rate_versions",
)

die_urlpatterns = [
    path("", include(die_routers.urls)),
    path(
        "diesize-import/",
        DieSizeBulkImportAPIView.as_view(),
        name="diesize_import",
    ),
    path(
        "diegroup-import/",
        DieGroupBulkImportAPIView.as_view(),
        name="diegroup_import",
    ),
    path(
        "diecategory-import/",
        DieCategoryBulkImportAPIView.as_view(),
        name="diecategory_import",
    ),
    path(
        "diesubcategory-import/",
        DieSubCategoryBulkImportAPIView.as_view(),
        name="diesubcategory_import",
    ),
    path(
        "section-import-async/",
        SectionAsyncImportAPIView.as_view(),
        name="section_import_async",
    ),
    path(
        "balloon-dimension-import-async/",
        BalloonDimensionAsyncImportAPIView.as_view(),
        name="balloon_dimension_import_async",
    ),
    path(
        "dietool-import-async/",
        DieToolAsyncImportAPIView.as_view(),
        name="dietool_import_async",
    ),
]