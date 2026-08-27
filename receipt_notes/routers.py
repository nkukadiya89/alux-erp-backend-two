from rest_framework.routers import DefaultRouter
from .views import GoodsReceiptNoteViewSet, GoodsReceiptNoteDetailViewSet

receipt_notes_router = DefaultRouter()

receipt_notes_router.register(
    r'grn',
    GoodsReceiptNoteViewSet,
    basename='goods-receipt-notes'
)

receipt_notes_router.register(
    r'grn-detail',
    GoodsReceiptNoteDetailViewSet,
    basename='goods-receipt-note-details'
)