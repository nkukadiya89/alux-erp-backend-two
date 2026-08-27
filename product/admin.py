from django.contrib import admin

from product.models import (
    Alloy,
    Item,
    ItemType,
    MaterialCenter,
    Temper,
    ValuationMethod,
    StandardMaster
)

admin.site.register(Temper)
admin.site.register(Alloy)
admin.site.register(Item)
admin.site.register(ItemType)
admin.site.register(ValuationMethod)
admin.site.register(MaterialCenter)
admin.site.register(StandardMaster)