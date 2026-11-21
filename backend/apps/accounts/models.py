"""Tài khoản người dùng với ba vai trò Shop, Nhân viên/Admin, Shipper."""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q
from django.utils.crypto import salted_hmac

from .constants import PHONE_INVALID_MESSAGE, PHONE_REGEX, AccountAction, UserRole

SESSION_HASH_SALT = "apps.accounts.models.User.get_session_auth_hash"


class UserManager(DjangoUserManager):
    use_in_migrations = True

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not extra_fields.get("role"):
            raise ValueError("Phải chỉ định vai trò (role) khi tạo người dùng.")
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        if extra_fields["role"] != UserRole.ADMIN:
            raise ValueError("Superuser phải có vai trò ADMIN.")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    # Dùng full_name thay cho cặp first_name/last_name.
    first_name = None
    last_name = None

    full_name = models.CharField("họ tên", max_length=150)
    phone = models.CharField(
        "số điện thoại",
        max_length=10,
        unique=True,
        validators=[RegexValidator(PHONE_REGEX, PHONE_INVALID_MESSAGE)],
    )
    role = models.CharField("vai trò", max_length=10, choices=UserRole.choices)
    address = models.CharField("địa chỉ liên hệ", max_length=255, blank=True)
    must_change_password = models.BooleanField("bắt buộc đổi mật khẩu", default=False)
    # Tăng mỗi lần khóa: mọi phiên cũ mất hiệu lực vĩnh viễn, mở khóa không làm sống lại (spec 003 mục 3.2).
    session_version = models.PositiveIntegerField("phiên bản phiên", default=0, editable=False)
    updated_at = models.DateTimeField("cập nhật lúc", auto_now=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["full_name", "phone"]

    class Meta:
        verbose_name = "người dùng"
        verbose_name_plural = "người dùng"
        # Khớp thứ tự danh sách quản lý tài khoản (role, username) và bộ lọc theo vai trò (spec 003).
        indexes = [models.Index(fields=["role", "username"], name="accounts_user_role_name_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=UserRole.values),
                name="accounts_user_role_valid",
            ),
            models.CheckConstraint(
                condition=Q(phone__regex=PHONE_REGEX),
                name="accounts_user_phone_format",
            ),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # --- Phiên đăng nhập ---
    # Django so hash này ở mọi request; băm kèm session_version để có thể vô hiệu hóa mọi phiên
    # mà không cần đổi mật khẩu hay quét bảng phiên. Ghi đè cả hàm fallback (dùng khi xoay SECRET_KEY).
    def _session_hash(self, secret=None):
        return salted_hmac(
            SESSION_HASH_SALT, f"{self.password}:{self.session_version}", secret=secret, algorithm="sha256"
        ).hexdigest()

    def get_session_auth_hash(self):
        return self._session_hash()

    def get_session_auth_fallback_hash(self):
        for fallback_secret in settings.SECRET_KEY_FALLBACKS:
            yield self._session_hash(secret=fallback_secret)

    def invalidate_sessions(self):
        """Mọi phiên đang có của tài khoản mất hiệu lực (tăng session_version, an toàn khi gọi đồng thời)."""
        type(self).objects.filter(pk=self.pk).update(session_version=F("session_version") + 1)
        self.refresh_from_db(fields=["session_version"])

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name

    @property
    def is_shop(self):
        return self.role == UserRole.SHOP

    @property
    def is_admin_role(self):
        return self.role == UserRole.ADMIN

    @property
    def is_shipper(self):
        return self.role == UserRole.SHIPPER


class AccountEvent(models.Model):
    """Lịch sử thao tác quản lý tài khoản (spec 003 D6). Chỉ thêm, không sửa/xóa; không chứa mật khẩu."""

    account = models.ForeignKey(
        User, verbose_name="tài khoản", on_delete=models.PROTECT, related_name="account_events",
        db_index=False,  # đã có index ghép bắt đầu bằng account (acct_event_account_idx)
    )
    actor = models.ForeignKey(
        User, verbose_name="người thực hiện", on_delete=models.PROTECT, null=True, blank=True,
        related_name="performed_account_events",
    )
    action = models.CharField("thao tác", max_length=20, choices=AccountAction.choices)
    changes = models.JSONField("thay đổi", blank=True, default=dict)
    reason = models.CharField("lý do", max_length=255, blank=True, default="")
    created_at = models.DateTimeField("lúc", auto_now_add=True)

    class Meta:
        verbose_name = "lịch sử tài khoản"
        verbose_name_plural = "lịch sử tài khoản"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["account", "-created_at", "-id"], name="acct_event_account_idx")]

    def __str__(self):
        return f"{self.get_action_display()} · {self.account_id}"
