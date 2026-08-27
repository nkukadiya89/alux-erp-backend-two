from rest_framework.routers import DefaultRouter

from .views import (
    BlosterMasterArchiveViewSet,
    BlosterMasterViewSet,
    DeleteBlosterUploadedFile,
    BlosterTypeViewSet,
)

bloster_routers = DefaultRouter()
bloster_routers.register("bloster", BlosterMasterViewSet, basename="bloster")
bloster_routers.register(
    "bloster-archive", viewset=BlosterMasterArchiveViewSet, basename="bloster_archive"
)
bloster_routers.register(
    "delete-bloster-files", DeleteBlosterUploadedFile, basename="delete_bloster_files"
)
bloster_routers.register("bloster-type", BlosterTypeViewSet, basename="bloster-type")
