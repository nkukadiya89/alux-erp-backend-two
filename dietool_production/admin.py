from django.contrib import admin
from .models import DieProductionLog, DieMaintenanceLog, DieTrialLog, MaintenanceType, CorrectionHistory


admin.site.register(DieProductionLog)
admin.site.register(DieMaintenanceLog)
admin.site.register(DieTrialLog)
admin.site.register(MaintenanceType)
admin.site.register(CorrectionHistory)