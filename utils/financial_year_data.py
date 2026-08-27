from datetime import date

from django.db.models import Q

from common.models import FinancialYearModel


def set_default_financial_year():
    today = date.today()
    current_year_obj = FinancialYearModel.objects.filter(
        start_date__lte=today, end_date__gte=today
    ).first()

    if current_year_obj:
        FinancialYearModel.objects.all().update(default=False)
        current_year_obj.default = True
        current_year_obj.save()
        return current_year_obj
    else:
        latest = FinancialYearModel.objects.order_by("-start_date").first()
        if latest:
            FinancialYearModel.objects.all().update(default=False)
            latest.default = True
            latest.save()
            return latest
    return None
