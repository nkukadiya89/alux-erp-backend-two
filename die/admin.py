from django.contrib import admin

from die.models import (
    ConversionRate,
    ConversionRateItems,
    ConversionRateVersions,
    Die,
    DieCategory,
    DieGroup,
    DiePress,
    DieSize,
    DieSubCategory,
    DieTool,
    DieType,
    SectionBallonDimensions,
    DieInformation,
    DieToolBrokenImage
)

admin.site.register(Die)
admin.site.register(DieTool)
admin.site.register(DieGroup)
admin.site.register(DieCategory)
admin.site.register(DieSize)
admin.site.register(DieSubCategory)
admin.site.register(DieType)
admin.site.register(DiePress)
admin.site.register(ConversionRate)
admin.site.register(ConversionRateItems)
admin.site.register(ConversionRateVersions)
admin.site.register(SectionBallonDimensions)
admin.site.register(DieInformation)
admin.site.register(DieToolBrokenImage)
