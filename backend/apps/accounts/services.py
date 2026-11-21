"""Nghiệp vụ tài khoản: đăng nhập, đăng xuất, hồ sơ, đổi mật khẩu (spec 002); quản lý tài khoản (spec 003)."""
import logging
import secrets
import string

from django.contrib.auth import authenticate, login, logout, password_validation, update_session_auth_hash
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction

from apps.core.errors import BusinessError, ErrorCode

from .constants import (
    LAST_ADMIN_MESSAGE,
    PHONE_TAKEN_MESSAGE,
    SELF_MANAGE_MESSAGE,
    STALE_ACCOUNT_MESSAGE,
    TEMP_PASSWORD_ALPHABET,
    TEMP_PASSWORD_LENGTH,
    USERNAME_TAKEN_MESSAGE,
    AccountAction,
    UserRole,
)
from .models import AccountEvent, User

# Trường người dùng tự sửa được trong hồ sơ (spec 002 D4) — cũng là trường Nhân viên sửa được (spec 003).
SELF_EDITABLE_FIELDS = ("full_name", "phone", "address")
MANAGED_EDITABLE_FIELDS = SELF_EDITABLE_FIELDS

logger = logging.getLogger(__name__)

_logout_hooks = []


def register_logout_hook(func):
    """Đăng ký hàm chạy trước khi đăng xuất, nhận `user` (vd spec 011 dừng GPS). Dùng được như decorator."""
    _logout_hooks.append(func)
    return func


def _django_request(request):
    # DRF Request bọc HttpRequest; login/logout của Django cần HttpRequest gốc.
    return getattr(request, "_request", request)


def login_user(request, username, password):
    """Đăng nhập; sai thông tin hoặc tài khoản bị khóa → cùng một lỗi (UC01.1 E1)."""
    # ModelBackend trả None cho cả sai mật khẩu, không tồn tại và is_active=False,
    # và vẫn chạy băm mật khẩu khi không tồn tại để không lộ qua thời gian phản hồi.
    user = authenticate(_django_request(request), username=username, password=password)
    if user is None:
        raise BusinessError(ErrorCode.INVALID_CREDENTIALS)
    login(_django_request(request), user)  # xoay session key, chống session fixation
    return user


def logout_user(request):
    """Xóa phiên phía server. Không đụng tới nhiệm vụ đang mở (UC01.2 BR1). Luôn thành công."""
    user = request.user if request.user and request.user.is_authenticated else None
    if user is not None:
        for hook in _logout_hooks:
            try:
                hook(user)
            except Exception:  # hook lỗi không được chặn việc đăng xuất
                logger.exception("Logout hook %s lỗi", getattr(hook, "__name__", hook))
    logout(_django_request(request))


def update_profile(user, data):
    """Ghi các trường hồ sơ được phép (UC02.2). Lỗi thì không trường nào được lưu."""
    fields = [name for name in SELF_EDITABLE_FIELDS if name in data]
    if not fields:
        return user
    for name in fields:
        setattr(user, name, data[name])
    try:
        with transaction.atomic():
            user.save(update_fields=[*fields, "updated_at"])
    except IntegrityError:
        # Hai người cùng lưu một số điện thoại: serializer đã kiểm tra nhưng DB là lớp chặn cuối.
        user.refresh_from_db()
        raise BusinessError(ErrorCode.VALIDATION_ERROR, fields={"phone": [PHONE_TAKEN_MESSAGE]})
    return user


def change_password(request, new_password):
    """Đổi mật khẩu của chính người đang đăng nhập (UC02.3).

    Giữ phiên hiện tại; các phiên khác của tài khoản hết hiệu lực. Không ghi mật khẩu vào log.
    """
    user = request.user
    with transaction.atomic():
        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
    update_session_auth_hash(_django_request(request), user)
    return user


# ---------------------------------------------------------------------------
# Spec 003 — Nhân viên quản lý tài khoản
# ---------------------------------------------------------------------------

def generate_temp_password(user):
    """Mật khẩu tạm ngẫu nhiên, đủ chữ hoa/thường/số và qua AUTH_PASSWORD_VALIDATORS (thử lại nếu bị từ chối)."""
    for _ in range(20):
        candidate = "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(TEMP_PASSWORD_LENGTH))
        if not (any(c in string.ascii_uppercase for c in candidate)
                and any(c in string.ascii_lowercase for c in candidate)
                and any(c in string.digits for c in candidate)):
            continue
        try:
            password_validation.validate_password(candidate, user)
        except DjangoValidationError:
            continue
        return candidate
    raise RuntimeError("Không sinh được mật khẩu tạm hợp lệ.")  # thực tế không xảy ra


def ensure_not_self(actor, user):
    """D1: Nhân viên không thao tác quản lý lên chính mình."""
    if actor.pk == user.pk:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, SELF_MANAGE_MESSAGE)


def _duplicate_field_error(data):
    """Đổi IntegrityError (hai người tạo/sửa cùng lúc) thành lỗi đúng trường."""
    fields = {}
    if data.get("username") and User.objects.filter(username__iexact=data["username"]).exists():
        fields["username"] = [USERNAME_TAKEN_MESSAGE]
    if data.get("phone") and User.objects.filter(phone=data["phone"]).exists():
        fields["phone"] = [PHONE_TAKEN_MESSAGE]
    return BusinessError(ErrorCode.VALIDATION_ERROR, fields=fields or {"phone": [PHONE_TAKEN_MESSAGE]})


def create_account(actor, data):
    """UC02.4 A1 / UC06.2. Trả (user, temp_password); mật khẩu tạm chỉ có trong giá trị trả về này."""
    password = generate_temp_password(User(**data))
    try:
        with transaction.atomic():
            user = User.objects.create_user(password=password, must_change_password=True, **data)
            AccountEvent.objects.create(account=user, actor=actor, action=AccountAction.CREATED,
                                        changes={"role": {"from": None, "to": user.role}})
    except IntegrityError:
        raise _duplicate_field_error(data) from None
    return user, password


def update_account(actor, pk, data, expected_updated_at):
    """UC02.4 / UC06.3. Chống ghi đè: so updated_at sau khi đã khóa bản ghi (UC06.3 E1)."""
    with transaction.atomic():
        user = User.objects.select_for_update().filter(pk=pk).first()
        if user is None:
            raise BusinessError(ErrorCode.NOT_FOUND)
        ensure_not_self(actor, user)
        if user.updated_at != expected_updated_at:
            raise BusinessError(ErrorCode.CONFLICT, STALE_ACCOUNT_MESSAGE)

        changes = {
            name: {"from": getattr(user, name), "to": data[name]}
            for name in MANAGED_EDITABLE_FIELDS
            if name in data and getattr(user, name) != data[name]
        }
        if not changes:
            return user
        for name, change in changes.items():
            setattr(user, name, change["to"])
        try:
            with transaction.atomic():
                user.save(update_fields=[*changes, "updated_at"])
        except IntegrityError:
            raise _duplicate_field_error({"phone": data.get("phone")}) from None
        AccountEvent.objects.create(account=user, actor=actor, action=AccountAction.UPDATED, changes=changes)
    return user


_account_locked_hooks = []


def register_account_locked_hook(func):
    """Đăng ký hàm chạy khi khóa tài khoản, nhận (actor, user) — spec 006: đánh dấu nhiệm vụ mở cần xử lý.

    Chạy TRONG transaction khóa tài khoản: hook lỗi thì việc khóa cũng hủy, để dữ liệu nhất quán.
    """
    _account_locked_hooks.append(func)
    return func


def _locked_target(pk):
    user = User.objects.select_for_update().filter(pk=pk).first()
    if user is None:
        raise BusinessError(ErrorCode.NOT_FOUND)
    return user


def lock_account(actor, pk, reason=""):
    """UC02.4 A2 / UC06.4. Đã khóa sẵn → trả hiện tại, không ghi lịch sử (E1.1)."""
    with transaction.atomic():
        target = User.objects.filter(pk=pk).only("role").first()  # vai trò không bao giờ đổi (D2)
        if target is None:
            raise BusinessError(ErrorCode.NOT_FOUND)
        if target.role == UserRole.ADMIN:
            # Khóa mọi ADMIN đang hoạt động theo thứ tự id TRƯỚC khi đếm: hai Admin khóa nhau cùng lúc
            # thì giao dịch sau phải đợi rồi thấy số liệu mới (không deadlock, không mất hết Admin — BR2).
            active_admin_ids = list(
                User.objects.select_for_update()
                .filter(role=UserRole.ADMIN, is_active=True)
                .order_by("pk")
                .values_list("pk", flat=True)
            )
        user = _locked_target(pk)
        ensure_not_self(actor, user)
        if not user.is_active:
            return user
        if user.role == UserRole.ADMIN and not [i for i in active_admin_ids if i != user.pk]:
            raise BusinessError(ErrorCode.LIMIT_REACHED, LAST_ADMIN_MESSAGE)

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        user.invalidate_sessions()  # phiên cũ mất hiệu lực, mở khóa cũng không sống lại
        AccountEvent.objects.create(account=user, actor=actor, action=AccountAction.LOCKED, reason=reason)
        for hook in _account_locked_hooks:
            hook(actor, user)
    return user


def unlock_account(actor, pk):
    """UC06.4 A1. Không khôi phục phiên cũ — người dùng đăng nhập lại (A1.3)."""
    with transaction.atomic():
        user = _locked_target(pk)
        ensure_not_self(actor, user)
        if user.is_active:
            return user
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
        AccountEvent.objects.create(account=user, actor=actor, action=AccountAction.UNLOCKED)
    return user


def reset_password(actor, pk):
    """UC01.3 A1: Nhân viên đã xác minh danh tính → cấp mật khẩu tạm. Trả (user, temp_password).

    Mật khẩu đổi nên mọi phiên cũ mất hiệu lực. Lịch sử chỉ ghi đã xác minh, không ghi mật khẩu.
    """
    with transaction.atomic():
        user = _locked_target(pk)
        ensure_not_self(actor, user)
        password = generate_temp_password(user)
        user.set_password(password)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        AccountEvent.objects.create(account=user, actor=actor, action=AccountAction.PASSWORD_RESET,
                                    changes={"identity_verified": True})
    return user, password
