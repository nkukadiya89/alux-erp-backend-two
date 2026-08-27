from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from .models import GoodsReceiptNote, GoodsReceiptNoteDetail
from .serializers import GoodsReceiptNoteListSerializer, GoodsReceiptNoteSerializer, GoodsReceiptNoteDetailSerializer

class GoodsReceiptNoteViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = GoodsReceiptNote.objects.all()
    serializer_class = GoodsReceiptNoteSerializer
    list_serializer_class = GoodsReceiptNoteListSerializer
    serching_fields = (
        BaseModelViewSet.serching_fields
       + ["vendor"]
)

class GoodsReceiptNoteDetailViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = GoodsReceiptNoteDetail.objects.all()
    serializer_class = GoodsReceiptNoteDetailSerializer
    search_fields = (
          BaseModelViewSet.serching_fields + [
            "grn",
            "item",
            "store",
            "heat_no",
         ]
     )