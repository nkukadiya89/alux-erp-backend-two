from django.contrib import admin

from settings.models import (
    CompanySettings,
    FinancialSettings,
    NotificationSettings,
    TaxComplianceSettings,
    TermAndConditionSettings,
    ProductionSettings,
)

admin.site.register(CompanySettings)
admin.site.register(NotificationSettings)
admin.site.register(TaxComplianceSettings)
admin.site.register(FinancialSettings)
admin.site.register(TermAndConditionSettings)
admin.site.register(ProductionSettings)