from django.contrib import admin
from aging.models import AgeingBatch, AgeingBatchDetail, AgeingTemperatureLog

admin.site.register(AgeingBatch)
admin.site.register(AgeingBatchDetail)
admin.site.register(AgeingTemperatureLog)
