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


S = ShipmentStatus
A = ShipmentAction
SHOP, ADMIN, SHIPPER = UserRole.SHOP, UserRole.ADMIN, UserRole.SHIPPER

# Điều kiện ngoài vai trò + trạng thái (sở hữu, lý do, số lần giao, COD, nơi giữ hàng)
# kiểm tra trong service — xem specs/001-nen-tang/spec.md mục 3.4.
SHIPMENT_TRANSITIONS = {
    A.CREATE_REQUEST: transition([], S.PENDING_APPROVAL, [SHOP]),                           # UC05.2
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
}

del S, A, SHOP, ADMIN, SHIPPER

# Mã yêu cầu / mã vận đơn — quyết định D2 (spec 001 mục 2).
REQUEST_CODE_PREFIX = "YC"
REQUEST_CODE_DIGITS = 8                       # YC00000123
TRACKING_CODE_PREFIX = "HTT"
TRACKING_CODE_DATE_FORMAT = "%y%m%d"          # HTT261120K7Q2M
TRACKING_CODE_RANDOM_LENGTH = 5
TRACKING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bỏ I, O, 0, 1 dễ nhầm

# COD — quyết định D3. Số nguyên VND.
COD_MAX_VND = 50_000_000
