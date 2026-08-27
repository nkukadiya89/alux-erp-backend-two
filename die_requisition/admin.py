from django.contrib import admin

from die_requisition.models import DieRequisition, DieRequisitionDetail

admin.site.register(DieRequisition)
admin.site.register(DieRequisitionDetail)
