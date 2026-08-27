from rest_framework.routers import DefaultRouter

from jobwork_invoice.views import JobworkInvoiceLineViewSet, JobworkInvoiceViewSet

jobwork_invoice_routers = DefaultRouter()

jobwork_invoice_routers.register(
    "jobwork-invoice", JobworkInvoiceViewSet, basename="jobwork_invoice"
)
jobwork_invoice_routers.register(
    "jobwork-invoice-item",
    JobworkInvoiceLineViewSet,
    basename="jobwork_invoice_item",
)
