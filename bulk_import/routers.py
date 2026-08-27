from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BulkImportView, ImportStatusView

# Create router for ViewSet-based views
bulkimportrouters = DefaultRouter()

# URL patterns for APIView-based views
bulk_import_urlpatterns = [
    path("bulk-import/", BulkImportView.as_view(), name="bulk_import"),
    path(
        "import-status/<uuid:job_id>/", ImportStatusView.as_view(), name="import_status"
    ),
]

# Register any ViewSet here if needed in future
# bulkimportrouters.register(r'some-viewset', SomeViewSet.as_view(), basename='some_viewset')
