"""Nghiệp vụ yêu cầu gửi hàng (spec 004). Mọi đổi trạng thái đi qua SHIPMENT_TRANSITIONS.

Quy ước đồng thời (spec 001 mục 3.6): khóa bản ghi (select_for_update) TRƯỚC, rồi mới kiểm tra trạng thái
và updated_at — để Shop sửa/hủy cùng lúc Nhân viên duyệt thì chỉ một bên thắng, không ghi đè.
"""
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.errors import BusinessError, ErrorCode
from apps.core.transitions import resolve_transition
from apps.notifications.constants import NotificationKind
from apps.notifications.services import notify

from .constants import (
    APPROVED_NOTICE_BODY,
    APPROVED_NOTICE_TITLE,
    DECISION_VERBS,
    NOT_PENDING_DECISION_MESSAGE,
    REJECTED_NOTICE_BODY,
    REJECTED_NOTICE_TITLE,
    STALE_FOR_DECISION_MESSAGE,
    TRACKING_CODE_MAX_ATTEMPTS,
    NOT_PENDING_CANCEL_MESSAGE,
    NOT_PENDING_UPDATE_MESSAGE,
    SHIPMENT_TRANSITIONS,
    STALE_SHIPMENT_MESSAGE,
    TRACKING_CODE_ALPHABET,
    TRACKING_CODE_DATE_FORMAT,
    TRACKING_CODE_PREFIX,
    TRACKING_CODE_RANDOM_LENGTH,
    HolderType,
    ShipmentAction,
    ShipmentStatus,
)
from .models import Shipment, ShipmentEvent, Ward
from .permissions import shipments_visible_to

# Trường nội dung Shop sửa được (D5). Không có shop/mã/trạng thái (UC05.1 BR2).
EDITABLE_FIELDS = (
    "sender_name", "sender_phone", "pickup_ward", "pickup_address",
    "receiver_name", "receiver_phone", "delivery_ward", "delivery_address",
    "package_description", "package_count", "weight_grams", "cod_amount", "note",
)


def generate_tracking_code(now=None):
    """Mã vận đơn (spec 001 D2, spec 005 D4): HTT + yyMMdd theo giờ nghiệp vụ (TIME_ZONE) + ký tự ngẫu nhiên.

    Ngẫu nhiên bằng `secrets` (khó đoán mã đơn người khác). Không tự kiểm tra trùng — unique DB + thử lại ở
    nơi gọi mới chặn được tranh chấp giữa các lần duyệt chạy song song.
    """
    local = timezone.localtime(now or timezone.now(), timezone.get_default_timezone())
    random_part = "".join(secrets.choice(TRACKING_CODE_ALPHABET) for _ in range(TRACKING_CODE_RANDOM_LENGTH))
    return f"{TRACKING_CODE_PREFIX}{local.strftime(TRACKING_CODE_DATE_FORMAT)}{random_part}"


def _resolve(action, status, role, invalid_message):
    """Như resolve_transition nhưng thay thông điệp INVALID_TRANSITION bằng câu cụ thể cho người dùng."""
    try:
        return resolve_transition(SHIPMENT_TRANSITIONS, action, status, role)
    except BusinessError as exc:
        if exc.code == ErrorCode.INVALID_TRANSITION:
            raise BusinessError(ErrorCode.INVALID_TRANSITION, invalid_message) from None
        raise


def lock_visible(user, pk):
    shipment = shipments_visible_to(user).select_for_update().filter(pk=pk).first()
    if shipment is None:
        raise BusinessError(ErrorCode.NOT_FOUND)
    return shipment


def _change_value(value):
    """Giá trị ghi vào lịch sử: phường ghi cả mã và tên (tên có thể đổi về sau)."""
    if isinstance(value, Ward):
        return {"code": value.code, "name": value.name}
    return value


def create_request(shop, data):
    """UC05.2. Shop lấy từ phiên (BR2); sinh mã yêu cầu + lịch sử trong một transaction; chưa có mã vận đơn (BR1)."""
    rule = resolve_transition(SHIPMENT_TRANSITIONS, ShipmentAction.CREATE_REQUEST, None, shop.role)
    with transaction.atomic():
        shipment = Shipment.objects.create(shop=shop, status=rule.target, holder_type=HolderType.SHOP, **data)
        shipment.request_code = Shipment.build_request_code(shipment.pk)
        shipment.save(update_fields=["request_code"])
        ShipmentEvent.objects.create(
            shipment=shipment, action=ShipmentAction.CREATE_REQUEST,
            from_status=None, to_status=rule.target, actor=shop,
        )
    return shipment


def update_request(shop, pk, data, expected_updated_at):
    """UC05.1. Chỉ khi Chờ xác nhận; bản cũ → CONFLICT; không đổi gì thì không ghi lịch sử."""
    with transaction.atomic():
        shipment = lock_visible(shop, pk)
        rule = _resolve(ShipmentAction.UPDATE_REQUEST, shipment.status, shop.role, NOT_PENDING_UPDATE_MESSAGE)
        if shipment.updated_at != expected_updated_at:
            raise BusinessError(ErrorCode.CONFLICT, STALE_SHIPMENT_MESSAGE)

        changes = {}
        for name in EDITABLE_FIELDS:
            if name in data and getattr(shipment, name) != data[name]:
                changes[name] = {"from": _change_value(getattr(shipment, name)), "to": _change_value(data[name])}
                setattr(shipment, name, data[name])
        if not changes:
            return shipment
        shipment.save(update_fields=[*changes, "updated_at"])
        ShipmentEvent.objects.create(
            shipment=shipment, action=ShipmentAction.UPDATE_REQUEST,
            from_status=shipment.status, to_status=rule.target, actor=shop, changes=changes,
        )
    return shipment


def cancel_request(shop, pk, reason=""):
    """UC05.5. Đã hủy sẵn → trả hiện tại (gửi lại); đã duyệt/từ chối → INVALID_TRANSITION (E1). Không xóa (BR1)."""
    with transaction.atomic():
        shipment = lock_visible(shop, pk)
        if shipment.status == ShipmentStatus.CANCELLED:
            return shipment
        rule = _resolve(ShipmentAction.CANCEL_REQUEST, shipment.status, shop.role, NOT_PENDING_CANCEL_MESSAGE)
        previous = shipment.status
        shipment.status = rule.target
        shipment.save(update_fields=["status", "updated_at"])
        ShipmentEvent.objects.create(
            shipment=shipment, action=ShipmentAction.CANCEL_REQUEST,
            from_status=previous, to_status=rule.target, actor=shop, reason=reason,
        )
    return shipment


# ---------- Spec 005: Nhân viên duyệt / từ chối ----------

def check_staff_action(staff, shipment, action, expected_updated_at, *, verb,
                       blocked_message=NOT_PENDING_DECISION_MESSAGE, stale_message=STALE_FOR_DECISION_MESSAGE):
    """Trên đơn ĐÃ KHÓA: kiểm trạng thái (theo bảng) rồi updated_at. Trả rule. Dùng chung spec 005–006+.

    Thứ tự giống update_request: trạng thái trước, phiên bản sau — đơn đã hủy thì báo "Đã hủy" (có ích hơn
    "dữ liệu cũ"). `blocked_message`: mẫu có {status} (nhãn trạng thái hiện tại) và {verb}.
    """
    message = blocked_message.format(status=ShipmentStatus(shipment.status).label, verb=verb)
    rule = _resolve(action, shipment.status, staff.role, message)
    if shipment.updated_at != expected_updated_at:
        raise BusinessError(ErrorCode.CONFLICT, stale_message)
    return rule


def _check_decision(staff, shipment, action, expected_updated_at):
    return check_staff_action(staff, shipment, action, expected_updated_at, verb=DECISION_VERBS[action])


def _save_with_new_tracking_code(shipment, fields):
    """Gán mã vận đơn mới rồi lưu; trùng unique (cực hiếm) thì sinh lại trong savepoint (spec 005 D4).

    Hết lượt vẫn trùng → SERVER_ERROR; transaction ngoài rollback nên không có vận đơn dở dang.
    """
    for _ in range(TRACKING_CODE_MAX_ATTEMPTS):
        shipment.tracking_code = generate_tracking_code()
        try:
            with transaction.atomic():
                shipment.save(update_fields=["tracking_code", *fields, "updated_at"])
            return
        except IntegrityError:
            continue
    shipment.tracking_code = None
    raise BusinessError(ErrorCode.SERVER_ERROR)


def approve_request(staff, pk, expected_updated_at):
    """UC05.6. Sinh mã vận đơn + Chờ lấy hàng + lịch sử + thông báo Shop trong một transaction.

    Đã có mã (gửi lại / Nhân viên khác vừa duyệt) → trả hiện tại, không sinh mã thứ hai (BR1, BR2, D3).
    """
    with transaction.atomic():
        shipment = lock_visible(staff, pk)
        if shipment.tracking_code:
            return shipment
        rule = _check_decision(staff, shipment, ShipmentAction.APPROVE_REQUEST, expected_updated_at)
        previous = shipment.status
        shipment.status = rule.target
        _save_with_new_tracking_code(shipment, ["status"])
        ShipmentEvent.objects.create(
            shipment=shipment, action=ShipmentAction.APPROVE_REQUEST, from_status=previous, to_status=rule.target,
            actor=staff, changes={"tracking_code": {"from": None, "to": shipment.tracking_code}},
        )
        notify(
            shipment.shop, NotificationKind.REQUEST_APPROVED,
            APPROVED_NOTICE_TITLE.format(request_code=shipment.request_code),
            APPROVED_NOTICE_BODY.format(tracking_code=shipment.tracking_code),
            payload={"shipment_id": shipment.pk},
        )
    return shipment


def reject_request(staff, pk, reason, expected_updated_at):
    """UC05.8. Bị từ chối + lý do (bắt buộc — serializer kiểm) + lịch sử + thông báo; không sinh mã vận đơn.

    Đã Bị từ chối sẵn → trả hiện tại (gửi lại, D3).
    """
    with transaction.atomic():
        shipment = lock_visible(staff, pk)
        if shipment.status == ShipmentStatus.REJECTED:
            return shipment
        rule = _check_decision(staff, shipment, ShipmentAction.REJECT_REQUEST, expected_updated_at)
        previous = shipment.status
        shipment.status = rule.target
        shipment.save(update_fields=["status", "updated_at"])
        ShipmentEvent.objects.create(
            shipment=shipment, action=ShipmentAction.REJECT_REQUEST, from_status=previous, to_status=rule.target,
            actor=staff, reason=reason,
        )
        notify(
            shipment.shop, NotificationKind.REQUEST_REJECTED,
            REJECTED_NOTICE_TITLE.format(request_code=shipment.request_code),
            REJECTED_NOTICE_BODY.format(reason=reason),
            payload={"shipment_id": shipment.pk},
        )
    return shipment
