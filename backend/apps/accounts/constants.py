"""Hằng số và enum của tài khoản. Nguồn duy nhất cho vai trò người dùng."""
from django.db import models


class UserRole(models.TextChoices):
    SHOP = "SHOP", "Shop"
    ADMIN = "ADMIN", "Nhân viên/Admin"
    SHIPPER = "SHIPPER", "Shipper"


class AccountAction(models.TextChoices):
    """Thao tác quản lý tài khoản ghi vào lịch sử (spec 003)."""

    CREATED = "CREATED", "Tạo tài khoản"
    UPDATED = "UPDATED", "Cập nhật hồ sơ"
    LOCKED = "LOCKED", "Khóa tài khoản"
    UNLOCKED = "UNLOCKED", "Mở khóa tài khoản"
    PASSWORD_RESET = "PASSWORD_RESET", "Đặt lại mật khẩu"


# Mật khẩu tạm do hệ thống sinh khi tạo tài khoản / đặt lại mật khẩu (spec 003 D3, D4).
TEMP_PASSWORD_LENGTH = 12
TEMP_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"  # bỏ 0 O 1 l I

# Số di động Việt Nam: 10 chữ số, bắt đầu bằng 0.
PHONE_REGEX = r"^0\d{9}$"
PHONE_INVALID_MESSAGE = "Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0."
PHONE_TAKEN_MESSAGE = "Số điện thoại đã được sử dụng."

# Tên đăng nhập do Nhân viên tạo (spec 003): chữ/số/. _ -, 3–150 ký tự.
USERNAME_REGEX = r"^[A-Za-z0-9._-]{3,150}$"
USERNAME_INVALID_MESSAGE = "Tên đăng nhập gồm 3–150 ký tự: chữ không dấu, số, dấu chấm, gạch dưới, gạch ngang."
USERNAME_TAKEN_MESSAGE = "Tên đăng nhập đã được sử dụng."

# Thông điệp nghiệp vụ quản lý tài khoản (spec 003).
SELF_MANAGE_MESSAGE = "Dùng trang Thông tin cá nhân / Đổi mật khẩu để thay đổi tài khoản của chính bạn."
STALE_ACCOUNT_MESSAGE = "Tài khoản vừa được người khác thay đổi. Vui lòng tải lại."
LAST_ADMIN_MESSAGE = "Không thể khóa Nhân viên/Admin đang hoạt động cuối cùng."
IDENTITY_NOT_VERIFIED_MESSAGE = "Cần xác minh danh tính trước khi đặt lại mật khẩu."
LOCK_REASON_MAX_LENGTH = 255
