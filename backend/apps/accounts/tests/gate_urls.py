"""URL chỉ dùng trong test chặn mật khẩu tạm."""
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.constants import UserRole
from apps.accounts.permissions import HasRole


class DefaultPermsView(APIView):  # dùng DEFAULT_PERMISSION_CLASSES
    def get(self, request):
        return Response({"ok": True})


class RoleView(APIView):  # tự khai báo permission_classes — vẫn phải bị chặn
    permission_classes = [HasRole.of(UserRole.SHOP, UserRole.ADMIN, UserRole.SHIPPER)]

    def get(self, request):
        return Response({"ok": True})


urlpatterns = [
    path("t/default/", DefaultPermsView.as_view()),
    path("t/role/", RoleView.as_view()),
    path("", include("config.urls")),
]
