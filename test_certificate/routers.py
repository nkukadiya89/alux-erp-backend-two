from rest_framework.routers import DefaultRouter
from .views import TestCertificateViewSet

test_certificate_router = DefaultRouter()

test_certificate_router.register(
    r"test-certificate", TestCertificateViewSet, basename="test-certificate"
)
