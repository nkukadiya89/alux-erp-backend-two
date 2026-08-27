from rest_framework.routers import DefaultRouter
from .views import MaterialIndentViewSet, MaterialDetailViewSet


material_indent_router = DefaultRouter()

material_indent_router.register(r"material-indents", MaterialIndentViewSet, basename="material-indent")
material_indent_router.register(r"material-indent-detail", MaterialDetailViewSet, basename="material-detail")
