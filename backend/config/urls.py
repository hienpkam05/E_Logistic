from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/shipments/", include("apps.shipments.urls")),
    path("api/v1/dispatch/", include("apps.dispatch.urls")),
    path("api/v1/tracking/", include("apps.tracking.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
]
