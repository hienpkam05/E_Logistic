"""Enum, bảng chuyển trạng thái và hằng số của nhiệm vụ lấy/giao/hoàn.

Trạng thái nhiệm vụ tách khỏi trạng thái vận đơn (đặc tả mục 2).
"""
from django.db import models

from apps.accounts.constants import UserRole
from apps.core.transitions import transition

# Tối đa số lần giao thực tế mỗi vận đơn, tính cả lần thành công (UC04.12 BR1).
MAX_DELIVERY_ATTEMPTS = 3


class TaskType(models.TextChoices):
    PICKUP = "PICKUP", "Lấy hàng"
    DELIVERY = "DELIVERY", "Giao hàng"
    RETURN = "RETURN", "Hoàn hàng"


class TaskStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Đang thực hiện"
    PENDING_SWAP_HANDOVER = "PENDING_SWAP_HANDOVER", "Chờ bàn giao đổi Shipper"
    SUCCEEDED = "SUCCEEDED", "Hoàn tất"
    FAILED = "FAILED", "Thất bại"
    REPLACED = "REPLACED", "Đã thay thế"


INITIAL_TASK_STATUS = TaskStatus.ACTIVE

TERMINAL_TASK_STATUSES = frozenset({TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.REPLACED})

# Nhiệm vụ còn "mở" — dùng cho ràng buộc một nhiệm vụ mở mỗi vận đơn.
OPEN_TASK_STATUSES = frozenset({TaskStatus.ACTIVE, TaskStatus.PENDING_SWAP_HANDOVER})


class TaskAction(models.TextChoices):
    TASK_SUCCEED = "TASK_SUCCEED", "Hoàn tất nhiệm vụ"
    TASK_FAIL = "TASK_FAIL", "Ghi nhận thất bại"
    TASK_REPLACE = "TASK_REPLACE", "Thay Shipper"
    TASK_START_SWAP = "TASK_START_SWAP", "Bắt đầu bàn giao đổi Shipper"
    TASK_CONFIRM_SWAP = "TASK_CONFIRM_SWAP", "Xác nhận bàn giao đổi Shipper"


T = TaskStatus
ADMIN, SHIPPER = UserRole.ADMIN, UserRole.SHIPPER

# Vai trò theo loại nhiệm vụ kiểm tra trong service:
# - TASK_SUCCEED: SHIPPER cho PICKUP/DELIVERY; ADMIN cho RETURN (xác nhận tiếp nhận UC04.9).
# - TASK_FAIL: chỉ PICKUP/DELIVERY.
# Ghi nhận bàn giao của Shipper không đổi trạng thái — chỉ ghi handover_reported_at.
TASK_TRANSITIONS = {
    TaskAction.TASK_SUCCEED: transition([T.ACTIVE], T.SUCCEEDED, [SHIPPER, ADMIN]),
    TaskAction.TASK_FAIL: transition([T.ACTIVE], T.FAILED, [SHIPPER]),
    TaskAction.TASK_REPLACE: transition([T.ACTIVE], T.REPLACED, [ADMIN]),                       # UC06.8, chưa giữ hàng
    TaskAction.TASK_START_SWAP: transition([T.ACTIVE], T.PENDING_SWAP_HANDOVER, [ADMIN]),       # UC06.8 A1
    TaskAction.TASK_CONFIRM_SWAP: transition([T.PENDING_SWAP_HANDOVER], T.REPLACED, [ADMIN]),   # UC06.8 A1.5
}

del T, ADMIN, SHIPPER
