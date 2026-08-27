from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from .models import Material
from .serializer import MaterialSerializer


class MaterialViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    search_fields = BaseModelViewSet.serching_fields + ["material_name"]

    ordering_fields = BaseModelViewSet.ordering_fields + ["id", "material_name"]
