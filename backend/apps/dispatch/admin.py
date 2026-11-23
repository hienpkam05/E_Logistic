"""Django admin cho nhiệm vụ / kết quả / bàn giao — CHỈ XEM (đổi trạng thái phải qua service)."""
from django.contrib import admin

from apps.shipments.admin import ReadOnlyAdmin

from .models import Handover, Task, TaskResult


@admin.register(Task)
class TaskAdmin(ReadOnlyAdmin):
    list_display = ("id", "shipment", "type", "status", "shipper", "assigned_at", "needs_attention")
    list_filter = ("type", "status", "needs_attention")
    search_fields = ("shipment__tracking_code", "shipper__username")
    list_select_related = ("shipment", "shipper")


@admin.register(TaskResult)
class TaskResultAdmin(ReadOnlyAdmin):
    list_display = ("task", "outcome", "reason_code", "recorded_by", "recorded_at")
    list_filter = ("outcome", "reason_code")
    list_select_related = ("task", "recorded_by")


@admin.register(Handover)
class HandoverAdmin(ReadOnlyAdmin):
    list_display = ("shipment", "kind", "from_shipper", "received_by", "receiver_name", "received_at")
    list_filter = ("kind",)
    list_select_related = ("shipment", "from_shipper", "received_by")
