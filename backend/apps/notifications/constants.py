"""Loại thông báo nội bộ. Spec sau thêm loại mới vào đây, không tự đặt chuỗi."""
from django.db import models


class NotificationKind(models.TextChoices):
    REQUEST_APPROVED = "REQUEST_APPROVED", "Yêu cầu đã được duyệt"
    REQUEST_REJECTED = "REQUEST_REJECTED", "Yêu cầu bị từ chối"
    TASK_ASSIGNED = "TASK_ASSIGNED", "Được phân công nhiệm vụ"
    TASK_REPLACED = "TASK_REPLACED", "Nhiệm vụ đã chuyển người khác"
    PICKED_UP = "PICKED_UP", "Đã lấy hàng"
    PICKUP_FAILED = "PICKUP_FAILED", "Lấy hàng thất bại"
    PICKUP_ABANDONED = "PICKUP_ABANDONED", "Kết thúc do không lấy được hàng"
    PICKUP_RETRY = "PICKUP_RETRY", "Sẽ lấy hàng lại"  # spec 006 D8
    DELIVERED = "DELIVERED", "Đã giao hàng"
    DELIVERY_FAILED = "DELIVERY_FAILED", "Giao hàng thất bại"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Đơn đang được giao"  # spec 007 D10
    REDELIVERY_SCHEDULED = "REDELIVERY_SCHEDULED", "Sẽ giao lại"  # spec 007 D10
    RETURN_DECIDED = "RETURN_DECIDED", "Đơn chuyển hoàn"
    RETURN_HANDOVER_REPORTED = "RETURN_HANDOVER_REPORTED", "Shipper đã đưa hàng hoàn về"  # spec 008 D9
    RETURN_AT_HUB = "RETURN_AT_HUB", "Hàng hoàn đã về điểm tập kết"
    RETURN_COMPLETED = "RETURN_COMPLETED", "Shop đã nhận hàng hoàn"
    ACCOUNT_LOCKED_TASKS = "ACCOUNT_LOCKED_TASKS", "Shipper bị khóa còn nhiệm vụ mở"
