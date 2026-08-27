from rest_framework.routers import DefaultRouter

from return_qc.views import ReturnQCLineViewSet, ReturnQCViewSet

return_qc_routers = DefaultRouter()

return_qc_routers.register("return-qc", ReturnQCViewSet, basename="return_qc")
return_qc_routers.register(
    "return-qc-item", ReturnQCLineViewSet, basename="return_qc_item"
)
