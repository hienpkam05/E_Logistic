"""Xem thông báo trong Django admin — chỉ đọc, không cho tạo/sửa/xóa."""
from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "kind", "title", "created_at", "read_at")
    list_filter = ("kind", ("read_at", admin.EmptyFieldListFilter))
    search_fields = ("title", "recipient__username", "recipient__full_name")
    list_select_related = ("recipient",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
