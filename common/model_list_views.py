from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.constants import UPLOADING_ALLOWED_MODELS


class ContentTypeListView(ModelViewSet):
    """
    Model view to list all content types (models) in the system.
    """

    queryset = ContentType.objects.filter(model__in=UPLOADING_ALLOWED_MODELS).order_by(
        "app_label", "model"
    )
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        content_types = self.get_queryset().values("id", "app_label", "model")
        return Response({"success": True, "data": list(content_types)}, status=200)
