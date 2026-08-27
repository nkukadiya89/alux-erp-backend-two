from rest_framework import serializers
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from .models import MaterialIndent, MaterialIndentDetail
from material_indent.serializers import MaterialIndentSerializer, MaterialDetailSerializer, MaterialIndentListSerializer

class MaterialIndentViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = MaterialIndent.objects.all()
    serializer_class = MaterialIndentSerializer
    list_serializer_class = MaterialIndentListSerializer
    search_fields = BaseModelViewSet.serching_fields + ["priority", "indent_no"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["id", "required_date"]

    
class MaterialDetailViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = MaterialIndentDetail.objects.all()
    serializer_class = MaterialDetailSerializer
    serching_fields = "__all__ "
    ordering_fields = BaseModelViewSet.ordering_fields + ["id", "item_material"]                  
