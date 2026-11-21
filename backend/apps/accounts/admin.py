"""Django admin cho User — công cụ kỹ thuật, không thay thế chức năng quản lý tài khoản (spec 003)."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AccountEvent, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "full_name", "phone", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "full_name", "phone")
    ordering = ("username",)
    readonly_fields = ("last_login", "date_joined", "updated_at")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Thông tin", {"fields": ("full_name", "phone", "email", "address")}),
        ("Vai trò và trạng thái", {"fields": ("role", "is_active", "must_change_password")}),
        (
            "Quyền Django admin",
            {"classes": ("collapse",), "fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Thời gian", {"fields": ("last_login", "date_joined", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "full_name", "phone", "role", "usable_password", "password1", "password2"),
            },
        ),
    )


@admin.register(AccountEvent)
class AccountEventAdmin(admin.ModelAdmin):
    """Lịch sử chỉ thêm (spec 003 D6): chỉ xem, không tạo/sửa/xóa."""

    list_display = ("created_at", "account", "action", "actor", "reason")
    list_filter = ("action",)
    search_fields = ("account__username", "actor__username")
    list_select_related = ("account", "actor")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
