"""API xác thực và hồ sơ cá nhân (spec 002). Chi tiết: specs/002-xac-thuc/api.md."""
from django.db.models import Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .constants import UserRole
from .models import AccountEvent, User
from .permissions import HasRole
from .serializers import (
    AccountCreateSerializer,
    AccountEventSerializer,
    AccountListQuerySerializer,
    AccountUpdateSerializer,
    LockAccountSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    ManagedUserSerializer,
    MeSerializer,
    MeUpdateSerializer,
)

IsAdminRole = HasRole.of(UserRole.ADMIN)


class CsrfView(APIView):
    """GET → đặt cookie csrftoken để frontend gửi kèm request ghi."""

    permission_classes = [AllowAny]
    allow_when_password_change_required = True

    def get(self, request):
        get_token(request._request)  # CsrfViewMiddleware gắn cookie vào response
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(APIView):
    permission_classes = [AllowAny]
    allow_when_password_change_required = True
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        # DRF miễn CSRF cho người chưa đăng nhập; bật lại để chống login CSRF.
        SessionAuthentication().enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.login_user(request, **serializer.validated_data)
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    """Luôn 204, kể cả khi phiên đã hết (UC01.2 A1)."""

    permission_classes = [AllowAny]
    allow_when_password_change_required = True

    def post(self, request):
        services.logout_user(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Hồ sơ của chính mình: xem (UC02.1), sửa (UC02.2). Khi phải đổi mật khẩu chỉ được xem."""

    allow_when_password_change_required = {"GET"}

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = services.update_profile(request.user, serializer.validated_data)
        return Response(MeSerializer(user).data)


class ChangePasswordView(APIView):
    """Đổi mật khẩu của chính mình (UC02.3); cũng là lối ra khỏi mật khẩu tạm (UC01.3)."""

    allow_when_password_change_required = True
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_change"  # theo tài khoản: chặn dò mật khẩu hiện tại

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        services.change_password(request, serializer.validated_data["new_password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Spec 003 — Nhân viên quản lý tài khoản. Chi tiết: specs/003-quan-ly-tai-khoan/api.md
# ---------------------------------------------------------------------------

class AccountCollectionView(ListAPIView):
    """GET: danh sách (UC02.4, UC06.1). POST: tạo tài khoản (UC02.4 A1, UC06.2)."""

    permission_classes = [IsAdminRole]
    serializer_class = ManagedUserSerializer

    def get_queryset(self):
        query = AccountListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        queryset = User.objects.order_by("role", "username")
        if params.get("role"):
            queryset = queryset.filter(role=params["role"])
        if params.get("is_active") is not None:
            queryset = queryset.filter(is_active=params["is_active"])
        if params.get("q", "").strip():
            term = params["q"].strip()
            queryset = queryset.filter(
                Q(username__icontains=term) | Q(full_name__icontains=term) | Q(phone__icontains=term)
            )
        return queryset

    def post(self, request):
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, temp_password = services.create_account(request.user, serializer.validated_data)
        return Response(
            {"user": ManagedUserSerializer(user).data, "temp_password": temp_password},
            status=status.HTTP_201_CREATED,
        )


class AccountDetailView(APIView):
    """GET: chi tiết. PATCH: sửa hồ sơ (UC02.4, UC06.3). Không có DELETE (BR1)."""

    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        return Response(ManagedUserSerializer(get_object_or_404(User, pk=pk)).data)

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        services.ensure_not_self(request.user, user)
        serializer = AccountUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "updated_at" not in data:
            raise ValidationError({"updated_at": ["Thiếu phiên bản dữ liệu đã tải (updated_at)."]})
        expected = data.pop("updated_at")
        user = services.update_account(request.user, pk, data, expected)
        return Response(ManagedUserSerializer(user).data)


class AccountLockView(APIView):
    """Khóa tài khoản (UC02.4 A2, UC06.4)."""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        serializer = LockAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.lock_account(request.user, pk, serializer.validated_data["reason"].strip())
        return Response(ManagedUserSerializer(user).data)


class AccountUnlockView(APIView):
    """Mở khóa (UC06.4 A1). Phiên cũ không dùng lại được."""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        return Response(ManagedUserSerializer(services.unlock_account(request.user, pk)).data)


class AccountResetPasswordView(APIView):
    """Đặt lại mật khẩu tạm sau khi Nhân viên xác minh danh tính (UC01.3 A1)."""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        get_object_or_404(User, pk=pk)  # 404 trước lỗi dữ liệu
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, temp_password = services.reset_password(request.user, pk)
        return Response({"user": ManagedUserSerializer(user).data, "temp_password": temp_password})


class AccountEventListView(ListAPIView):
    """Lịch sử thao tác của một tài khoản, mới nhất trước. Chỉ đọc."""

    permission_classes = [IsAdminRole]
    serializer_class = AccountEventSerializer

    def get_queryset(self):
        account = get_object_or_404(User, pk=self.kwargs["pk"])
        return AccountEvent.objects.filter(account=account).select_related("actor")
