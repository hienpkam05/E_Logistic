"""Enum, bảng chuyển trạng thái và hằng số của nhiệm vụ lấy/giao/hoàn.

Trạng thái nhiệm vụ tách khỏi trạng thái vận đơn (đặc tả mục 2).
"""
from django.db import models

from apps.accounts.constants import UserRole
from apps.core.transitions import transition
# shipments.constants không import dispatch → không vòng. MAX_DELIVERY_ATTEMPTS đặt ở shipments (ràng buộc trên
# Shipment.delivery_attempts); nhập lại ở đây để code điều phối dùng một chỗ.
from apps.shipments.constants import MAX_DELIVERY_ATTEMPTS, ShipmentAction  # noqa: F401


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


# Kết quả cuối ghi vào TaskResult (tập con của TaskStatus — chỉ kết quả do người phụ trách ghi).
TASK_OUTCOMES = (TaskStatus.SUCCEEDED, TaskStatus.FAILED)


class PickupFailReason(models.TextChoices):
    """Lý do lấy hàng thất bại (spec 006 D4). Nhãn hiển thị qua /meta/choices/ (pickup_fail_reasons)."""

    SHOP_ABSENT = "SHOP_ABSENT", "Shop vắng mặt / không liên lạc được"
    NOT_READY = "NOT_READY", "Hàng chưa sẵn sàng"
    WRONG_ADDRESS = "WRONG_ADDRESS", "Sai địa chỉ lấy"
    SHOP_DECLINED = "SHOP_DECLINED", "Shop không muốn gửi nữa"
    MISMATCH = "MISMATCH", "Hàng không đúng mô tả"
    OTHER = "OTHER", "Khác"


class DeliveryFailReason(models.TextChoices):
    """Lý do giao hàng thất bại (spec 007 D4). Nhãn qua /meta/choices/ (delivery_fail_reasons).

    Chung cột TaskResult.reason_code với PickupFailReason: chỉ được trùng mã khi cùng nhãn (OTHER) — có test canh.
    """

    RECEIVER_UNREACHABLE = "RECEIVER_UNREACHABLE", "Không liên hệ được người nhận"
    RECEIVER_RESCHEDULED = "RECEIVER_RESCHEDULED", "Người nhận hẹn giao lại"
    RECEIVER_REFUSED = "RECEIVER_REFUSED", "Người nhận từ chối nhận"
    COD_NOT_READY = "COD_NOT_READY", "Người nhận chưa đủ tiền COD"
    ADDRESS_NOT_FOUND = "ADDRESS_NOT_FOUND", "Sai / không tìm thấy địa chỉ giao"
    OTHER = "OTHER", "Khác"


# Lý do thất bại theo loại nhiệm vụ (RETURN không có thất bại — TASK_FAIL chỉ PICKUP/DELIVERY).
FAIL_REASONS_BY_TASK_TYPE = {
    TaskType.PICKUP: PickupFailReason,
    TaskType.DELIVERY: DeliveryFailReason,
}
# choices của TaskResult.reason_code: hợp các nhóm, bỏ mã trùng (giữ thứ tự xuất hiện).
TASK_RESULT_REASON_CHOICES = list(dict.fromkeys(
    choice for enum in FAIL_REASONS_BY_TASK_TYPE.values() for choice in enum.choices
))


class HandoverKind(models.TextChoices):
    """Loại bàn giao hàng (spec 001 mục 6). Spec 008–009 thêm hoàn về điểm tập kết, đổi Shipper, Shop nhận hoàn."""

    HUB_INTAKE = "HUB_INTAKE", "Nhập điểm tập kết"
    RETURN_INTAKE = "RETURN_INTAKE", "Tiếp nhận hàng hoàn"  # spec 008 — UC04.9
    SHOP_PICKUP = "SHOP_PICKUP", "Shop nhận hàng hoàn"  # spec 008 — UC04.11


# Độ dài ghi chú (kết quả nhiệm vụ, sai lệch khi bàn giao) — khớp cột lý do lịch sử vận đơn.
RESULT_NOTE_MAX_LENGTH = 500
HANDOVER_NOTE_MAX_LENGTH = 500
RECEIVER_NAME_MAX_LENGTH = 100  # spec 008: người nhận hàng hoàn phía Shop — như độ dài họ tên người nhận


# ---- Spec 006: thao tác của Nhân viên trên đơn (khuôn chung với duyệt/từ chối — shipments.services) ----
# {status}: nhãn trạng thái hiện tại; {verb}: STAFF_ACTION_VERBS[hành động].
STAFF_ACTION_BLOCKED_MESSAGE = "Vận đơn đang ở trạng thái {status} nên không {verb} được."
STALE_FOR_STAFF_MESSAGE = "Vận đơn vừa được cập nhật. Vui lòng tải lại để kiểm tra trước khi xử lý."
SHIPPER_UNAVAILABLE_MESSAGE = "Shipper không còn hoạt động. Vui lòng chọn Shipper khác."
ALREADY_ASSIGNED_MESSAGE = "Đơn đã được phân công cho {name}. Muốn đổi người hãy dùng chức năng đổi Shipper."
ALREADY_ASSIGNED_UNKNOWN_NAME = "Shipper khác"  # khi DB chặn trùng (partial unique) — không biết ngay là ai
FAIL_REASON_WITH_NOTE = "{reason} — {note}"  # lý do lấy thất bại ghi vào lịch sử + thông báo
REASON_REQUIRED_MESSAGE = "Vui lòng nhập lý do."
SHIPPER_PICKER_LIMIT = 200  # danh sách chọn Shipper không phân trang; chặn trên để phản hồi luôn nhỏ

# Thông báo (D8, D9).
TASK_ASSIGNED_TITLE = "Nhiệm vụ lấy hàng mới: {code}"
TASK_ASSIGNED_BODY = "Lấy tại {address}, {ward} — {shop}."
PICKUP_RETRY_TITLE = "Vận đơn {code} sẽ được lấy lại"
PICKUP_ABANDONED_TITLE = "Vận đơn {code} kết thúc do không lấy được hàng"
REASON_BODY = "Lý do: {reason}"
LOCKED_TASKS_TITLE = "Shipper {name} bị khóa khi còn {count} nhiệm vụ đang mở"
LOCKED_TASKS_BODY = "Cần đổi Shipper cho các nhiệm vụ này."
# Phía Shipper (UC04.1–04.3).
TASK_CLOSED_MESSAGE = "Nhiệm vụ đã kết thúc hoặc đã chuyển cho người khác. Vui lòng tải lại danh sách."
FAIL_NOTE_REQUIRED_MESSAGE = "Chọn lý do Khác thì cần ghi chú cụ thể."
PICKED_UP_TITLE = "Vận đơn {code} đã được lấy"
PICKED_UP_BODY = "Shipper {name} đã nhận hàng, đang chờ đưa về điểm tập kết."
PICKUP_FAILED_TITLE = "Lấy hàng thất bại: {code}"

# ---- Spec 007: giao hàng, COD, giao lại / hoàn ----
# Thông điệp lỗi. {diff}, {expected}: số tiền đã định dạng VND.
COD_SHORT_MESSAGE = "Thiếu {diff} so với COD phải thu {expected}."
COD_OVER_MESSAGE = "Thừa {diff} so với COD phải thu {expected}."
HOLDER_ONLY_MESSAGE = (
    "Hàng đang ở Shipper {name}. Muốn dùng người khác cần bàn giao hàng về điểm tập kết (đổi Shipper)."
)
HANDOVER_REQUIRED_MESSAGE = "Vui lòng xác nhận Shipper đã nhận hàng trước khi phân công giao."
DELIVERY_LIMIT_MESSAGE = "Vận đơn đã giao {count}/{max} lần nên chỉ được chuyển hoàn."
# Thông báo (D10).
DELIVERY_TASK_ASSIGNED_TITLE = "Nhiệm vụ giao hàng mới: {code}"
DELIVERY_TASK_ASSIGNED_BODY = "Giao cho {receiver} tại {address}, {ward} — lần {attempt}/{max}."
OUT_FOR_DELIVERY_TITLE = "Vận đơn {code} đang được giao"
OUT_FOR_DELIVERY_BODY = "Shipper {name} đang giao lần {attempt}/{max}."
DELIVERED_TITLE = "Vận đơn {code} đã giao thành công"
DELIVERED_COD_BODY = "Đã thu COD {amount}."
DELIVERY_FAILED_TITLE = "Giao hàng thất bại: {code} (lần {attempt}/{max})"
REDELIVERY_SCHEDULED_TITLE = "Vận đơn {code} sẽ được giao lại"
RETURN_DECIDED_TITLE = "Vận đơn {code} chuyển hoàn về Shop"

# ---- Spec 008: hoàn hàng ----
RECEIVER_NAME_REQUIRED_MESSAGE = "Vui lòng nhập tên người nhận."
RETURN_ALREADY_AT_HUB_MESSAGE = "Hàng đã ở điểm tập kết — không cần chuyến hoàn, hãy dùng \"Tiếp nhận hàng hoàn\"."
RETURN_NEEDS_TRIP_MESSAGE = "Hàng đang ở Shipper {name} — cần phân công hoàn để đưa về điểm tập kết trước."
VERIFIED_REQUIRED_MESSAGE = "Vui lòng xác nhận đã kiểm tra người nhận thuộc Shop hoặc được Shop ủy quyền."
RETURN_TASK_ASSIGNED_TITLE = "Nhiệm vụ hoàn hàng mới: {code}"
RETURN_TASK_ASSIGNED_BODY = "Đưa hàng về {hub}: {address}."
RETURN_HANDOVER_REPORTED_TITLE = "Shipper {name} đã đưa hàng hoàn {code} về điểm tập kết"
RETURN_HANDOVER_REPORTED_BODY = "Kiểm tra mã đơn, số kiện, tình trạng hàng rồi xác nhận tiếp nhận."
RETURN_AT_HUB_TITLE = "Hàng hoàn {code} đã về điểm tập kết"
RETURN_AT_HUB_BODY = "Mời Shop đến nhận tại {hub}: {address} (SĐT {phone})."
RETURN_COMPLETED_TITLE = "Shop đã nhận lại hàng hoàn {code}"
RETURN_COMPLETED_BODY = "Người nhận: {name}."


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

# Động từ trong thông điệp chặn (mẫu STAFF_ACTION_BLOCKED_MESSAGE).
STAFF_ACTION_VERBS = {
    ShipmentAction.ASSIGN_PICKUP: "phân công lấy hàng",
    ShipmentAction.RECEIVE_AT_HUB: "xác nhận tiếp nhận",
    ShipmentAction.RETRY_PICKUP: "chuyển lấy lại",
    ShipmentAction.ABANDON_PICKUP: "kết thúc",
    ShipmentAction.ASSIGN_DELIVERY: "phân công giao hàng",  # spec 007
    ShipmentAction.DECIDE_REDELIVERY: "chuyển giao lại",
    ShipmentAction.DECIDE_RETURN: "chuyển hoàn",
    ShipmentAction.ASSIGN_RETURN: "phân công hoàn hàng",  # spec 008
    ShipmentAction.RECEIVE_RETURN: "tiếp nhận hàng hoàn",
    ShipmentAction.REPORT_RETURN_ISSUE: "ghi sai lệch hàng hoàn",
    ShipmentAction.CONFIRM_SHOP_RECEIVED: "xác nhận Shop nhận hàng",
}
