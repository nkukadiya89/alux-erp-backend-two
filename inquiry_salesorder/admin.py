from django.contrib import admin

from inquiry_salesorder.models import InquirySalesOrder, InquirySalesOrderDetail

admin.site.register(InquirySalesOrder)
admin.site.register(InquirySalesOrderDetail)
