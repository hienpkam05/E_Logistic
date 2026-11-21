"""Permission dùng chung theo vai trò và trạng thái mật khẩu.

Chỉ kiểm tra đăng nhập + tài khoản hoạt động + mật khẩu tạm + vai trò. Quyền sở hữu/phân công
đặt trong permissions.py của từng app nghiệp vụ.
"""
from rest_framework.permissions import BasePermission

from apps.core.errors import BusinessError, ErrorCode

ALLOW_FLAG = "allow_when_password_change_required"


def view_allows_temp_password(view, request):
    """View đánh dấu ALLOW_FLAG = True (mọi method) hoặc tập method, vd {"GET"}."""
    flag = getattr(view, ALLOW_FLAG, False)
    if isinstance(flag, (set, frozenset, list, tuple)):
        return request.method in flag
    return bool(flag)


class PasswordChangeNotRequired(BasePermission):
    """Chặn tài khoản đang dùng mật khẩu tạm (spec 002 D5).

    Người chưa đăng nhập: không xử lý ở đây (IsAuthenticated/HasRole lo).
    """

    def has_permission(self, request, view):
        user = request.user
        if (
            user
            and user.is_authenticated
            and getattr(user, "must_change_password", False)
            and not view_allows_temp_password(view, request)
        ):
            raise BusinessError(ErrorCode.PASSWORD_CHANGE_REQUIRED)
        return True


class HasRole(PasswordChangeNotRequired):
    """Dùng: permission_classes = [HasRole.of(UserRole.ADMIN)].

    Kế thừa chặn mật khẩu tạm để view tự khai báo permission_classes không vô tình bỏ qua.
    """

    allowed_roles: frozenset = frozenset()

    @classmethod
    def of(cls, *roles):
        if not roles:
            raise ValueError("HasRole.of() cần ít nhất một vai trò.")
        name = "HasRole_" + "_".join(sorted(str(r) for r in roles))
        return type(name, (cls,), {"allowed_roles": frozenset(roles)})

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        super().has_permission(request, view)
        return user.role in self.allowed_roles
