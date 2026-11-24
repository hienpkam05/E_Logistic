"""Tổng hợp enum và giới hạn nghiệp vụ cho endpoint /api/v1/meta/choices/.

Thêm enum mới mà frontend cần hiển thị: đăng ký vào CHOICE_GROUPS (test sẽ báo nếu quên).
"""
from django.conf import settings
from apps.tracking.constants import (
    PING_MAX_AGE_SECONDS, PING_MAX_FUTURE_SECONDS, PING_MIN_INTERVAL_SECONDS, PING_MAX_ACCURACY_M,
    LOCATION_STALE_SECONDS, LOCATION_RETENTION_DAYS, LOCATION_POLL_INTERVAL_SECONDS,
)

from apps.accounts.constants import AccountAction, UserRole
from apps.core.constants import SEARCH_QUERY_MAX_LENGTH
from apps.dispatch.constants import (
    HANDOVER_NOTE_MAX_LENGTH,
    MAX_DELIVERY_ATTEMPTS,
    RECEIVER_NAME_MAX_LENGTH,
    RESULT_NOTE_MAX_LENGTH,
    TERMINAL_TASK_STATUSES,
    DeliveryFailReason,
    HandoverKind,
    PickupFailReason,
    TaskAction,
    TaskStatus,
    TaskType,
)
from apps.notifications.constants import NotificationKind
from apps.shipments.constants import (
    CANCEL_REASON_MAX_LENGTH,
    COD_MAX_VND,
    EVENT_REASON_MAX_LENGTH,
    PACKAGE_COUNT_MAX,
    PACKAGE_COUNT_MIN,
    TERMINAL_SHIPMENT_STATUSES,
    WEIGHT_GRAMS_MAX,
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
    "pickup_fail_reasons": (PickupFailReason, None),  # spec 006
    "handover_kinds": (HandoverKind, None),  # spec 006
    "delivery_fail_reasons": (DeliveryFailReason, None),  # spec 007
}

LIMITS = {
    "location_ping_max_age_seconds": PING_MAX_AGE_SECONDS,
    "location_ping_max_future_seconds": PING_MAX_FUTURE_SECONDS,
    "location_ping_min_interval_seconds": PING_MIN_INTERVAL_SECONDS,
    "location_ping_max_accuracy_m": PING_MAX_ACCURACY_M,
    "location_stale_seconds": LOCATION_STALE_SECONDS,
    "location_poll_interval_seconds": LOCATION_POLL_INTERVAL_SECONDS,
    "location_retention_days": LOCATION_RETENTION_DAYS,
    "max_delivery_attempts": MAX_DELIVERY_ATTEMPTS,
    "cod_max_vnd": COD_MAX_VND,
    # Spec 004: form yêu cầu gửi hàng dùng để đặt giới hạn ô nhập (không chép số sang frontend).
    "package_count_min": PACKAGE_COUNT_MIN,
    "package_count_max": PACKAGE_COUNT_MAX,
    "weight_grams_max": WEIGHT_GRAMS_MAX,
    # Spec 004 Phase 6: độ dài ô nhập lấy từ backend (trước đây frontend viết thẳng 100).
    "search_query_max_length": SEARCH_QUERY_MAX_LENGTH,
    "cancel_reason_max_length": CANCEL_REASON_MAX_LENGTH,
    "reject_reason_max_length": EVENT_REASON_MAX_LENGTH,  # spec 005: ô lý do từ chối
    # Spec 006: lý do lấy lại / kết thúc, ghi chú lấy thất bại; ghi chú sai lệch khi nhập điểm tập kết.
    "task_note_max_length": RESULT_NOTE_MAX_LENGTH,
    "handover_note_max_length": HANDOVER_NOTE_MAX_LENGTH,
    # Spec 008: tên người nhận hàng hoàn phía Shop (hộp "Xác nhận Shop đã nhận").
    "handover_receiver_name_max_length": RECEIVER_NAME_MAX_LENGTH,
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
    data["hub"] = dict(settings.HUB)  # spec 008 D6: điểm tập kết (tên, địa chỉ, SĐT)
    return data
