from rest_framework.routers import DefaultRouter
from .views import DrossEntryViewSet, DrossDetailViewSet

create_dross_entry_routers = DefaultRouter()
create_dross_entry_routers.register(r'dross-entry', DrossEntryViewSet, basename='dross-entry')
create_dross_entry_routers.register(r'dross-detail', DrossDetailViewSet, basename='dross-detail')