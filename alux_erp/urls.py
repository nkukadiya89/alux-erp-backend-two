"""
URL configuration for alux_erp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from alux_erp.routers import alux_router
from bulk_import.routers import bulk_import_urlpatterns
from gate_entry.routers import gate_entry_extra_urlpatterns
from scrap_transfer.routers import scrap_transfer_extra_urlpatterns
from scrap_generation_remelt.routers import scrap_generation_remelt_extra_urlpatterns
from dashboard.dashboard_views import DashboardAPIView
from settings.routers import settings_extra_urls
from user.user_auth import CustomTokenObtainPairView, TokenRefreshView
from customer.routers import customertype_urlpatterns
from die.routers import die_urlpatterns
from common.routers import common_urlpatterns


from .views import root_status

urlpatterns = [
    path("", root_status),
    path("admin/", admin.site.urls),
    path("get-token/", CustomTokenObtainPairView.as_view(), name="get_token"),
    path("refresh-token/", TokenRefreshView.as_view(), name="refresh_token"),
    path("api/v1/silk/", include("silk.urls", namespace="silk")),  
    path("api/v1/", include(alux_router.urls)),
    path("api/v1/", include(settings_extra_urls)),
    path("api/v1/", include(bulk_import_urlpatterns)),
    path("api/v1/", include(gate_entry_extra_urlpatterns)),
    path("api/v1/", include(scrap_transfer_extra_urlpatterns)),
    path("api/v1/", include(scrap_generation_remelt_extra_urlpatterns)),
    path("api/v1/", include(customertype_urlpatterns)),
    path("api/v1/", include(die_urlpatterns)),
    path("api/v1/", include(common_urlpatterns)),
    path("dashboard", DashboardAPIView.as_view(), name="dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
