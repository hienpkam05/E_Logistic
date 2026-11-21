"""Tổng hợp enum và giới hạn nghiệp vụ cho endpoint /api/v1/meta/choices/.

Thêm enum mới mà frontend cần hiển thị: đăng ký vào CHOICE_GROUPS (test sẽ báo nếu quên).
"""
from apps.accounts.constants import AccountAction, UserRole
from apps.dispatch.constants import MAX_DELIVERY_ATTEMPTS, TERMINAL_TASK_STATUSES, TaskAction, TaskStatus, TaskType
from apps.notifications.constants import NotificationKind
from apps.shipments.constants import (
    COD_MAX_VND,
    TERMINAL_SHIPMENT_STATUSES,
    HolderType,
    ShipmentAction,
    ShipmentStatus,
)

# tên nhóm trong JSON -> (enum, tập trạng thái kết thúc hoặc None nếu không áp dụng)
CHOICE_GROUPS = {
    "user_roles": (UserRole, None),
    "account_actions": (AccountAction, None),
    "shipment_statuses": (ShipmentStatus, TERMINAL_SHIPMENT_STATUSES),
    "shipment_actions": (ShipmentAction, None),
    "holder_types": (HolderType, None),
    "task_types": (TaskType, None),
    "task_statuses": (TaskStatus, TERMINAL_TASK_STATUSES),
    "task_actions": (TaskAction, None),
    "notification_kinds": (NotificationKind, None),
}

LIMITS = {
    "max_delivery_attempts": MAX_DELIVERY_ATTEMPTS,
    "cod_max_vnd": COD_MAX_VND,
}


def _serialize(enum, terminal):
    items = []
    for value, label in enum.choices:
        item = {"value": value, "label": str(label)}
        if terminal is not None:
            item["terminal"] = value in terminal
        items.append(item)
    return items


def build_choices():
    data = {name: _serialize(enum, terminal) for name, (enum, terminal) in CHOICE_GROUPS.items()}
    data["limits"] = dict(LIMITS)
    return data
