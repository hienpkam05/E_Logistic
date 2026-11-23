"""Enum, bảng chuyển trạng thái và hằng số của vận đơn.

Nguồn duy nhất — model, service, serializer và endpoint /meta/choices/ import từ đây.
Bảng chuyển trạng thái bám theo docs/HTT_EXPRESS_Checklist_chuc_nang.md mục 4.
"""
from django.db import models

from apps.accounts.constants import UserRole
from apps.core.transitions import transition


class ShipmentStatus(models.TextChoices):
    PENDING_APPROVAL = "PENDING_APPROVAL", "Chờ xác nhận"
    CANCELLED = "CANCELLED", "Đã hủy"
    REJECTED = "REJECTED", "Bị từ chối"
    AWAITING_PICKUP = "AWAITING_PICKUP", "Chờ lấy hàng"
    PICKUP_ASSIGNED = "PICKUP_ASSIGNED", "Đã phân công lấy hàng"
    PICKED_UP = "PICKED_UP", "Đã lấy hàng"
    PICKUP_FAILED = "PICKUP_FAILED", "Lấy hàng thất bại"
    PICKUP_ABANDONED = "PICKUP_ABANDONED", "Kết thúc do không lấy được hàng"
    AT_HUB = "AT_HUB", "Đã nhập điểm tập kết"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Đang giao hàng"
    DELIVERED = "DELIVERED", "Đã giao hàng"
    DELIVERY_FAILED = "DELIVERY_FAILED", "Giao hàng thất bại"
    AWAITING_REDELIVERY = "AWAITING_REDELIVERY", "Chờ giao lại"
    AWAITING_RETURN = "AWAITING_RETURN", "Chờ xử lý hoàn"
    RETURNING = "RETURNING", "Đang hoàn"
    AWAITING_SHOP_PICKUP = "AWAITING_SHOP_PICKUP", "Chờ Shop đến lấy"
    RETURNED_TO_SHOP = "RETURNED_TO_SHOP", "Đã hoàn về Shop"


INITIAL_SHIPMENT_STATUS = ShipmentStatus.PENDING_APPROVAL

TERMINAL_SHIPMENT_STATUSES = frozenset({
    ShipmentStatus.CANCELLED,
    ShipmentStatus.REJECTED,
    ShipmentStatus.PICKUP_ABANDONED,
    ShipmentStatus.DELIVERED,
    ShipmentStatus.RETURNED_TO_SHOP,
})


class HolderType(models.TextChoices):
    """Ai/nơi nào đang giữ kiện hàng."""

    SHOP = "SHOP", "Shop"
    SHIPPER = "SHIPPER", "Shipper"
    HUB = "HUB", "Điểm tập kết"
    RECIPIENT = "RECIPIENT", "Người nhận"


class ShipmentAction(models.TextChoices):
    CREATE_REQUEST = "CREATE_REQUEST", "Tạo yêu cầu gửi hàng"
    UPDATE_REQUEST = "UPDATE_REQUEST", "Sửa yêu cầu"
    CANCEL_REQUEST = "CANCEL_REQUEST", "Hủy yêu cầu"
    REJECT_REQUEST = "REJECT_REQUEST", "Từ chối yêu cầu"
    APPROVE_REQUEST = "APPROVE_REQUEST", "Duyệt yêu cầu"
    ASSIGN_PICKUP = "ASSIGN_PICKUP", "Phân công lấy hàng"
    CONFIRM_PICKUP = "CONFIRM_PICKUP", "Xác nhận lấy hàng thành công"
    FAIL_PICKUP = "FAIL_PICKUP", "Cập nhật lấy hàng thất bại"
    RETRY_PICKUP = "RETRY_PICKUP", "Quyết định lấy lại"
    ABANDON_PICKUP = "ABANDON_PICKUP", "Kết thúc do không lấy được hàng"
    RECEIVE_AT_HUB = "RECEIVE_AT_HUB", "Xác nhận nhập điểm tập kết"
    ASSIGN_DELIVERY = "ASSIGN_DELIVERY", "Phân công giao hàng"
    CONFIRM_DELIVERY = "CONFIRM_DELIVERY", "Xác nhận giao hàng thành công"
    FAIL_DELIVERY = "FAIL_DELIVERY", "Cập nhật giao hàng thất bại"
    DECIDE_REDELIVERY = "DECIDE_REDELIVERY", "Quyết định giao lại"
    DECIDE_RETURN = "DECIDE_RETURN", "Quyết định hoàn hàng"
    ASSIGN_RETURN = "ASSIGN_RETURN", "Phân công hoàn hàng"
    RECEIVE_RETURN = "RECEIVE_RETURN", "Tiếp nhận hàng hoàn"
    CONFIRM_SHOP_RECEIVED = "CONFIRM_SHOP_RECEIVED", "Xác nhận Shop nhận hàng hoàn"
    # Spec 008: không đổi trạng thái nhưng cần mốc lịch sử → đi qua bảng như UPDATE_REQUEST.
    REPORT_RETURN_HANDOVER = "REPORT_RETURN_HANDOVER", "Shipper báo đã đưa hàng hoàn về"
    REPORT_RETURN_ISSUE = "REPORT_RETURN_ISSUE", "Ghi sai lệch hàng hoàn"


S = ShipmentStatus
A = ShipmentAction
SHOP, ADMIN, SHIPPER = UserRole.SHOP, UserRole.ADMIN, UserRole.SHIPPER

# Điều kiện ngoài vai trò + trạng thái (sở hữu, lý do, số lần giao, COD, nơi giữ hàng)
# kiểm tra trong service — xem specs/001-nen-tang/spec.md mục 3.4.
SHIPMENT_TRANSITIONS = {
    A.CREATE_REQUEST: transition([], S.PENDING_APPROVAL, [SHOP]),                           # UC05.2
    # Sửa không đổi trạng thái nhưng vẫn đi qua bảng để kiểm vai trò + trạng thái (checklist mục 4).
    A.UPDATE_REQUEST: transition([S.PENDING_APPROVAL], S.PENDING_APPROVAL, [SHOP]),         # UC05.1
    A.CANCEL_REQUEST: transition([S.PENDING_APPROVAL], S.CANCELLED, [SHOP]),                # UC05.5
    A.REJECT_REQUEST: transition([S.PENDING_APPROVAL], S.REJECTED, [ADMIN]),                # UC05.8
    A.APPROVE_REQUEST: transition([S.PENDING_APPROVAL], S.AWAITING_PICKUP, [ADMIN]),        # UC05.6
    A.ASSIGN_PICKUP: transition([S.AWAITING_PICKUP], S.PICKUP_ASSIGNED, [ADMIN]),           # UC06.5
    A.CONFIRM_PICKUP: transition([S.PICKUP_ASSIGNED], S.PICKED_UP, [SHIPPER]),              # UC04.2
    A.FAIL_PICKUP: transition([S.PICKUP_ASSIGNED], S.PICKUP_FAILED, [SHIPPER]),             # UC04.3
    A.RETRY_PICKUP: transition([S.PICKUP_FAILED], S.AWAITING_PICKUP, [ADMIN]),              # UC04.13
    A.ABANDON_PICKUP: transition([S.PICKUP_FAILED], S.PICKUP_ABANDONED, [ADMIN]),           # UC04.13
    A.RECEIVE_AT_HUB: transition([S.PICKED_UP], S.AT_HUB, [ADMIN]),                         # UC04.10
    A.ASSIGN_DELIVERY: transition(                                                          # UC06.6
        [S.AT_HUB, S.AWAITING_REDELIVERY], S.OUT_FOR_DELIVERY, [ADMIN]
    ),
    A.CONFIRM_DELIVERY: transition([S.OUT_FOR_DELIVERY], S.DELIVERED, [SHIPPER]),           # UC04.5, 04.7
    A.FAIL_DELIVERY: transition([S.OUT_FOR_DELIVERY], S.DELIVERY_FAILED, [SHIPPER]),        # UC04.6
    A.DECIDE_REDELIVERY: transition([S.DELIVERY_FAILED], S.AWAITING_REDELIVERY, [ADMIN]),   # UC04.12
    A.DECIDE_RETURN: transition([S.DELIVERY_FAILED], S.AWAITING_RETURN, [ADMIN]),           # UC04.12
    A.ASSIGN_RETURN: transition([S.AWAITING_RETURN], S.RETURNING, [ADMIN]),                 # UC06.7
    A.RECEIVE_RETURN: transition(                                                           # UC04.9, 06.7 A1.2
        [S.RETURNING, S.AWAITING_RETURN], S.AWAITING_SHOP_PICKUP, [ADMIN]
    ),
    A.CONFIRM_SHOP_RECEIVED: transition([S.AWAITING_SHOP_PICKUP], S.RETURNED_TO_SHOP, [ADMIN]),  # UC04.11
    A.REPORT_RETURN_HANDOVER: transition([S.RETURNING], S.RETURNING, [SHIPPER]),            # UC04.9 bước 1–3, A1
    A.REPORT_RETURN_ISSUE: transition([S.RETURNING], S.RETURNING, [ADMIN]),                 # UC04.9 E1
}

del S, A, SHOP, ADMIN, SHIPPER

# Mã yêu cầu / mã vận đơn — quyết định D2 (spec 001 mục 2).
REQUEST_CODE_PREFIX = "YC"
REQUEST_CODE_DIGITS = 8                       # YC00000123
TRACKING_CODE_PREFIX = "HTT"
TRACKING_CODE_DATE_FORMAT = "%y%m%d"          # HTT261120K7Q2M
TRACKING_CODE_RANDOM_LENGTH = 5
TRACKING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bỏ I, O, 0, 1 dễ nhầm
TRACKING_CODE_MAX_ATTEMPTS = 5               # spec 005 D4: trùng mã (unique) thì thử lại, quá số lần → 500
TRACKING_CODE_REGEX = (
    rf"^{TRACKING_CODE_PREFIX}\d{{6}}[{TRACKING_CODE_ALPHABET}]{{{TRACKING_CODE_RANDOM_LENGTH}}}$"
)

# COD — quyết định D3. Số nguyên VND.
COD_MAX_VND = 50_000_000

# Tối đa số lần giao thực tế mỗi vận đơn, tính cả lần thành công (UC04.12 BR1). Đặt ở đây vì ràng buộc
# nằm trên Shipment.delivery_attempts (spec 007); dispatch dùng lại, shipments không import dispatch.
MAX_DELIVERY_ATTEMPTS = 3

# Kiện hàng và độ dài trường — spec 004 D3.
PACKAGE_COUNT_MIN = 1
PACKAGE_COUNT_MAX = 99
WEIGHT_GRAMS_MAX = 100_000
ADDRESS_MAX_LENGTH = 255
DESCRIPTION_MAX_LENGTH = 255
NOTE_MAX_LENGTH = 500
EVENT_REASON_MAX_LENGTH = 500                # cột lý do của lịch sử vận đơn (mọi hành động)
CANCEL_REASON_MAX_LENGTH = EVENT_REASON_MAX_LENGTH

# Phường/xã demo (spec 004 D1) — dữ liệu giả, thay bằng danh sách chính thức qua `load_wards`.
DEMO_WARD_PREFIX = "[Demo]"
WARD_NOT_IN_HANOI_MESSAGE = "Địa chỉ phải thuộc Hà Nội (chọn phường/xã trong danh sách)."
NOT_PENDING_UPDATE_MESSAGE = "Yêu cầu không còn ở trạng thái Chờ xác nhận nên không sửa được."
NOT_PENDING_CANCEL_MESSAGE = "Yêu cầu không còn ở trạng thái Chờ xác nhận nên không hủy được."
STALE_SHIPMENT_MESSAGE = "Yêu cầu vừa được thay đổi. Vui lòng tải lại."
MISSING_VERSION_MESSAGE = "Thiếu phiên bản dữ liệu đã tải (updated_at)."  # sửa / duyệt / từ chối

# Spec 005 — Nhân viên duyệt / từ chối. {status}: nhãn trạng thái hiện tại; {verb}: DECISION_VERBS.
NOT_PENDING_DECISION_MESSAGE = "Yêu cầu đang ở trạng thái {status} nên không {verb} được."
STALE_FOR_DECISION_MESSAGE = "Yêu cầu vừa được Shop thay đổi. Vui lòng tải lại để kiểm tra trước khi xử lý."
REJECT_REASON_REQUIRED_MESSAGE = "Vui lòng nhập lý do từ chối."
DECISION_VERBS = {ShipmentAction.APPROVE_REQUEST: "duyệt", ShipmentAction.REJECT_REQUEST: "từ chối"}
DATE_RANGE_INVALID_MESSAGE = "Đến ngày phải bằng hoặc sau Từ ngày."
# Sắp xếp danh sách (D7): giá trị tham số `ordering` -> order_by. Luôn kèm id để phân trang ổn định.
SHIPMENT_LIST_ORDERINGS = {
    "-created_at": ("-created_at", "-id"),  # mặc định: mới nhất trước
    "created_at": ("created_at", "id"),     # tab Chờ xác nhận: cũ nhất trước (xử lý theo thứ tự đến)
}
DEFAULT_SHIPMENT_ORDERING = "-created_at"
# Thông báo cho Shop (D6).
APPROVED_NOTICE_TITLE = "Yêu cầu {request_code} đã được duyệt"
APPROVED_NOTICE_BODY = "Mã vận đơn {tracking_code}. Đơn đang chờ lấy hàng."
REJECTED_NOTICE_TITLE = "Yêu cầu {request_code} bị từ chối"
REJECTED_NOTICE_BODY = "Lý do: {reason}"
