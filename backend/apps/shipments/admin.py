"""Django admin cho vận đơn — công cụ kỹ thuật.

Vận đơn và lịch sử CHỈ XEM: đổi trạng thái phải qua service/bảng chuyển trạng thái, không sửa tay trong admin.
Phường/xã sửa được (tên, đang dùng) nhưng không xóa — nạp hàng loạt bằng lệnh `load_wards`.
"""
from django.contrib import admin

from .models import Shipment, ShipmentEvent, Ward


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Shipment)
class ShipmentAdmin(ReadOnlyAdmin):
    list_display = ("request_code", "tracking_code", "shop", "status", "receiver_name", "cod_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("request_code", "tracking_code", "receiver_name", "receiver_phone", "shop__username")
    list_select_related = ("shop",)
    date_hierarchy = "created_at"


@admin.register(ShipmentEvent)
class ShipmentEventAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "shipment", "action", "from_status", "to_status", "actor")
    list_filter = ("action",)
    list_select_related = ("shipment", "actor")
    date_hierarchy = "created_at"
