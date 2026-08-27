from django.contrib import admin
from .models import VehicleMaster

from simple_history.admin import SimpleHistoryAdmin

@admin.register(VehicleMaster)
class VehicleMasterAdmin(SimpleHistoryAdmin):
    pass