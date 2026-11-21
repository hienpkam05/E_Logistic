from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import api_not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/shipments/", include("apps.shipments.urls")),
    path("api/v1/dispatch/", include("apps.dispatch.urls")),
    path("api/v1/tracking/", include("apps.tracking.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    # Luôn để cuối: mọi đường dẫn /api/.../ không khớp trả JSON 404.
    # Chỉ bắt URL có dấu "/" cuối để APPEND_SLASH vẫn chuyển hướng URL thiếu "/".
    re_path(r"^api/(?:.*/)?$", api_not_found),
]
