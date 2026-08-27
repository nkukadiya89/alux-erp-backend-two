from django.contrib import admin

from vendor.models import BankDetails, KeyPersons, Vendor

# Register your models here.


admin.site.register(Vendor)
admin.site.register(KeyPersons)
admin.site.register(BankDetails)
