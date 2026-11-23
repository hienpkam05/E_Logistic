from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.core.constants import SEARCH_QUERY_MAX_LENGTH

from .constants import (
    IDENTITY_NOT_VERIFIED_MESSAGE,
    LOCK_REASON_MAX_LENGTH,
    PHONE_INVALID_MESSAGE,
    PHONE_REGEX,
    PHONE_TAKEN_MESSAGE,
    USERNAME_INVALID_MESSAGE,
    USERNAME_REGEX,
    USERNAME_TAKEN_MESSAGE,
    UserRole,
)
from .models import AccountEvent, User


def phone_field(**kwargs):
    """Ô số điện thoại dùng chung: định dạng + không trùng người khác (tự bỏ qua chính bản ghi đang sửa)."""
    return serializers.CharField(
        max_length=10,
        validators=[
            RegexValidator(PHONE_REGEX, PHONE_INVALID_MESSAGE),
            UniqueValidator(queryset=User.objects.all(), message=PHONE_TAKEN_MESSAGE),
        ],
        **kwargs,
    )


# --- Spec 002: tài khoản của chính mình ---

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class MeSerializer(serializers.ModelSerializer):
    """Hồ sơ của chính người đang đăng nhập. Không bao giờ có mật khẩu/cờ quản trị (UC02.1 BR1)."""

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "phone", "address", "role", "must_change_password", "date_joined"]
        read_only_fields = fields


class MeUpdateSerializer(serializers.ModelSerializer):
    """Chỉ ba trường người dùng tự sửa (spec 002 D4). Trường khác gửi lên bị bỏ qua."""

    phone = phone_field()

    class Meta:
        model = User
        fields = ["full_name", "phone", "address"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    new_password_confirm = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def validate_current_password(self, value):
        if not self.context["user"].check_password(value):
            raise serializers.ValidationError("Mật khẩu hiện tại không đúng.")
        return value

    def validate(self, attrs):
        user = self.context["user"]
        new = attrs["new_password"]
        errors = {}
        if new != attrs["new_password_confirm"]:
            errors["new_password_confirm"] = ["Mật khẩu nhập lại không khớp."]
        if new == attrs["current_password"]:
            errors.setdefault("new_password", []).append("Mật khẩu mới phải khác mật khẩu hiện tại.")
        try:
            password_validation.validate_password(new, user)
        except DjangoValidationError as exc:
            errors.setdefault("new_password", []).extend(exc.messages)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


# --- Spec 003: Nhân viên quản lý tài khoản ---

class ManagedUserSerializer(serializers.ModelSerializer):
    """Tài khoản nhìn từ phía quản lý. Không có mật khẩu, hash, session_version, cờ Django admin (UC06.1 BR1)."""

    class Meta:
        model = User
        fields = [
            "id", "username", "full_name", "phone", "address", "role", "is_active",
            "must_change_password", "last_login", "date_joined", "updated_at",
        ]
        read_only_fields = fields


class AccountListQuerySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)
    is_active = serializers.BooleanField(required=False, default=None, allow_null=True)
    q = serializers.CharField(required=False, allow_blank=True, max_length=SEARCH_QUERY_MAX_LENGTH)


class AccountCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150,
        validators=[
            RegexValidator(USERNAME_REGEX, USERNAME_INVALID_MESSAGE),
            UniqueValidator(queryset=User.objects.all(), message=USERNAME_TAKEN_MESSAGE, lookup="iexact"),
        ],
    )
    phone = phone_field()
    role = serializers.ChoiceField(choices=UserRole.choices)

    class Meta:
        model = User
        fields = ["username", "full_name", "phone", "address", "role"]


class AccountUpdateSerializer(serializers.ModelSerializer):
    """Sửa hồ sơ (UC02.4, UC06.3). `updated_at` là phiên bản client đã tải — chống ghi đè (UC06.3 E1)."""

    phone = phone_field()
    updated_at = serializers.DateTimeField(write_only=True)

    class Meta:
        model = User
        fields = ["full_name", "phone", "address", "updated_at"]


class LockAccountSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=LOCK_REASON_MAX_LENGTH, default="")


class ResetPasswordSerializer(serializers.Serializer):
    identity_verified = serializers.BooleanField(required=False, default=False)

    def validate_identity_verified(self, value):
        if value is not True:
            raise serializers.ValidationError(IDENTITY_NOT_VERIFIED_MESSAGE)
        return value


class EventActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "full_name"]
        read_only_fields = fields


class AccountEventSerializer(serializers.ModelSerializer):
    actor = EventActorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = AccountEvent
        fields = ["id", "action", "actor", "changes", "reason", "created_at"]
        read_only_fields = fields
