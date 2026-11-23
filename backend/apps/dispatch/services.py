"""Nghiệp vụ điều phối lấy hàng (spec 006), giao hàng / COD / giao lại (spec 007), hoàn hàng (spec 008). Đổi trạng thái chỉ qua SHIPMENT_TRANSITIONS / TASK_TRANSITIONS.

Quy ước (spec 001 mục 3.6):
- Khóa theo thứ tự cố định ĐƠN → USER (Shipper được chọn) → NHIỆM VỤ để hai thao tác chạy song song không deadlock.
- Kiểm "đã xong" (gửi lại) TRƯỚC, rồi trạng thái, rồi updated_at (thao tác Nhân viên).
- Đơn + nhiệm vụ + kết quả/bàn giao + lịch sử + thông báo ghi trong MỘT transaction.
"""
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.core.errors import BusinessError, ErrorCode
from apps.core.formatting import format_vnd
from apps.core.transitions import resolve_transition
from apps.notifications.constants import NotificationKind
from apps.notifications.services import notify
from apps.shipments.constants import SHIPMENT_TRANSITIONS, HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.rules import guard_allows, has_delivery_attempts_left
from apps.shipments.services import check_staff_action, lock_visible

from .constants import (
    ALREADY_ASSIGNED_MESSAGE,
    RETURN_HANDOVER_REPORTED_BODY,
    RETURN_HANDOVER_REPORTED_TITLE,
    RETURN_ALREADY_AT_HUB_MESSAGE,
    RETURN_AT_HUB_BODY,
    RETURN_AT_HUB_TITLE,
    RETURN_COMPLETED_BODY,
    RETURN_COMPLETED_TITLE,
    RETURN_NEEDS_TRIP_MESSAGE,
    RETURN_TASK_ASSIGNED_BODY,
    RETURN_TASK_ASSIGNED_TITLE,
    DELIVERY_LIMIT_MESSAGE,
    DELIVERY_TASK_ASSIGNED_BODY,
    DELIVERY_TASK_ASSIGNED_TITLE,
    HOLDER_ONLY_MESSAGE,
    MAX_DELIVERY_ATTEMPTS,
    OUT_FOR_DELIVERY_BODY,
    OUT_FOR_DELIVERY_TITLE,
    REDELIVERY_SCHEDULED_TITLE,
    RETURN_DECIDED_TITLE,
    ALREADY_ASSIGNED_UNKNOWN_NAME,
    FAIL_REASON_WITH_NOTE,
    PICKED_UP_BODY,
    PICKED_UP_TITLE,
    PICKUP_FAILED_TITLE,
    TASK_CLOSED_MESSAGE,
    TASK_TRANSITIONS,
    FAIL_REASONS_BY_TASK_TYPE,
    COD_OVER_MESSAGE,
    COD_SHORT_MESSAGE,
    DELIVERED_COD_BODY,
    DELIVERED_TITLE,
    DELIVERY_FAILED_TITLE,
    TaskAction,
    LOCKED_TASKS_BODY,
    LOCKED_TASKS_TITLE,
    OPEN_TASK_STATUSES,
    PICKUP_ABANDONED_TITLE,
    PICKUP_RETRY_TITLE,
    REASON_BODY,
    SHIPPER_UNAVAILABLE_MESSAGE,
    STAFF_ACTION_BLOCKED_MESSAGE,
    STAFF_ACTION_VERBS,
    STALE_FOR_STAFF_MESSAGE,
    TASK_ASSIGNED_BODY,
    TASK_ASSIGNED_TITLE,
    HandoverKind,
    TaskStatus,
    TaskType,
)
from .models import Handover, Task, TaskResult
from .permissions import tasks_visible_to


def _check(staff, shipment, action, expected_updated_at):
    return check_staff_action(
        staff, shipment, action, expected_updated_at, verb=STAFF_ACTION_VERBS[action],
        blocked_message=STAFF_ACTION_BLOCKED_MESSAGE, stale_message=STALE_FOR_STAFF_MESSAGE,
    )


def _person(user):
    """Giá trị ghi vào changes của lịch sử (giữ tên tại thời điểm đó)."""
    return {"id": user.pk, "name": user.full_name} if user else None


def _open_task(shipment):
    return shipment.tasks.select_for_update().filter(status__in=OPEN_TASK_STATUSES).select_related("shipper").first()


def _last_event_is(shipment, action, actor):
    last = shipment.events.order_by("-created_at", "-id").first()
    return last is not None and last.action == action and last.actor_id == actor.pk


def _active_staff():
    return User.objects.filter(role=UserRole.ADMIN, is_active=True)


def _record(shipment, action, previous, actor, *, task=None, reason="", changes=None):
    ShipmentEvent.objects.create(
        shipment=shipment, action=action, from_status=previous, to_status=shipment.status,
        actor=actor, task=task, reason=reason, changes=changes or {},
    )


# ---------------------------------------------------------------- UC06.5 Phân công lấy hàng

def _resend_of_assignment(shipment, task_type, shipper_id):
    """Đơn đã có nhiệm vụ mở: cùng loại + cùng Shipper → gửi lại (True); khác → 409.

    Đổi người dùng UC06.8 (spec 009) — không tạo phân công song song (UC06.5 BR2, UC06.6 BR3).
    """
    current = _open_task(shipment)
    if current is None:
        return False
    if current.type == task_type and current.shipper_id == shipper_id:
        return True
    raise BusinessError(ErrorCode.CONFLICT, ALREADY_ASSIGNED_MESSAGE.format(name=current.shipper.full_name))


def _lock_available_shipper(shipper_id):
    """Khóa dòng Shipper: chạy nối tiếp với "khóa tài khoản" (spec 003 cũng khóa dòng này) — không phân công cho
    người vừa bị khóa (UC06.5 E1, UC06.6 E1)."""
    shipper = User.objects.select_for_update().filter(pk=shipper_id).first()
    if shipper is None or shipper.role != UserRole.SHIPPER or not shipper.is_active:
        raise BusinessError(ErrorCode.CONFLICT, SHIPPER_UNAVAILABLE_MESSAGE)
    return shipper


def _create_task(shipment, task_type, shipper, staff, **extra):
    try:
        with transaction.atomic():  # partial unique là lớp chặn cuối nếu có đường nào bỏ qua kiểm tra trước đó
            return Task.objects.create(shipment=shipment, type=task_type, shipper=shipper, assigned_by=staff, **extra)
    except IntegrityError:
        raise BusinessError(
            ErrorCode.CONFLICT, ALREADY_ASSIGNED_MESSAGE.format(name=ALREADY_ASSIGNED_UNKNOWN_NAME)
        ) from None


def assign_pickup(staff, shipment_id, shipper_id, expected_updated_at):
    """Tạo nhiệm vụ lấy cho Shipper đang hoạt động; đơn sang Đã phân công lấy hàng; báo Shipper.

    Gửi lại (đơn đã có nhiệm vụ lấy mở của CHÍNH Shipper này) → trả hiện tại. Đã giao cho người khác → 409.
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        if _resend_of_assignment(shipment, TaskType.PICKUP, shipper_id):
            return shipment
        rule = _check(staff, shipment, ShipmentAction.ASSIGN_PICKUP, expected_updated_at)
        shipper = _lock_available_shipper(shipper_id)
        task = _create_task(shipment, TaskType.PICKUP, shipper, staff)

        previous = shipment.status
        shipment.status = rule.target
        shipment.save(update_fields=["status", "updated_at"])
        _record(shipment, ShipmentAction.ASSIGN_PICKUP, previous, staff, task=task,
                changes={"shipper": {"from": None, "to": _person(shipper)}})
        notify(
            shipper, NotificationKind.TASK_ASSIGNED,
            TASK_ASSIGNED_TITLE.format(code=shipment.display_code),
            TASK_ASSIGNED_BODY.format(address=shipment.pickup_address, ward=shipment.pickup_ward.name,
                                      shop=shipment.sender_name),
            payload={"shipment_id": shipment.pk, "task_id": task.pk},
        )
    return shipment


# ---------------------------------------------------------------- UC04.10 Nhập điểm tập kết

def receive_at_hub(staff, shipment_id, discrepancy_note, expected_updated_at):
    """Nhân viên nhận hàng từ Shipper đang giữ: ghi bàn giao, đơn Đã nhập điểm tập kết, hàng ở điểm tập kết.

    Đã tiếp nhận rồi → trả hiện tại, không ghi bàn giao thứ hai (E1.1).
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        if shipment.status == ShipmentStatus.AT_HUB and _last_event_is(shipment, ShipmentAction.RECEIVE_AT_HUB, staff):
            return shipment
        rule = _check(staff, shipment, ShipmentAction.RECEIVE_AT_HUB, expected_updated_at)
        pickup_task = (shipment.tasks.filter(type=TaskType.PICKUP, status=TaskStatus.SUCCEEDED)
                       .order_by("-assigned_at", "-id").first())
        from_shipper = shipment.holder_shipper
        Handover.objects.create(
            shipment=shipment, task=pickup_task, kind=HandoverKind.HUB_INTAKE, from_shipper=from_shipper,
            received_by=staff, received_at=timezone.now(), discrepancy_note=discrepancy_note,
        )
        previous = shipment.status
        shipment.status = rule.target
        shipment.holder_type = HolderType.HUB
        shipment.holder_shipper = None
        shipment.save(update_fields=["status", "holder_type", "holder_shipper", "updated_at"])
        changes = {"holder": {"from": _person(from_shipper), "to": {"name": HolderType.HUB.label}}}
        if discrepancy_note:
            changes["discrepancy_note"] = {"from": None, "to": discrepancy_note}
        _record(shipment, ShipmentAction.RECEIVE_AT_HUB, previous, staff, task=pickup_task, changes=changes)
    return shipment


# ---------------------------------------------------------------- UC04.13 Xử lý lấy hàng thất bại

def _staff_decision(staff, shipment_id, reason, expected_updated_at, action, kind, title, *, guard=None):
    """Quyết định của Nhân viên có lý do bắt buộc (UC04.13, UC04.12): đổi trạng thái, ghi lý do, báo Shop.

    Gửi lại (đơn đã ở trạng thái đích do chính người này quyết định) → trả hiện tại. `guard(shipment)`: điều kiện
    phụ (vd: còn lượt giao), kiểm SAU trạng thái + phiên bản.
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        if shipment.status == SHIPMENT_TRANSITIONS[action].target and _last_event_is(shipment, action, staff):
            return shipment
        rule = _check(staff, shipment, action, expected_updated_at)
        if guard is not None:
            guard(shipment)
        previous = shipment.status
        shipment.status = rule.target
        shipment.save(update_fields=["status", "updated_at"])
        _record(shipment, action, previous, staff, reason=reason)
        notify(shipment.shop, kind, title.format(code=shipment.display_code), REASON_BODY.format(reason=reason),
               payload={"shipment_id": shipment.pk})
    return shipment


def retry_pickup(staff, shipment_id, reason, expected_updated_at):
    """Lấy lại → Chờ lấy hàng; Nhân viên phân công lại qua UC06.5. Lịch sử lần trước giữ nguyên (BR1)."""
    return _staff_decision(staff, shipment_id, reason, expected_updated_at, ShipmentAction.RETRY_PICKUP,
                           NotificationKind.PICKUP_RETRY, PICKUP_RETRY_TITLE)


def abandon_pickup(staff, shipment_id, reason, expected_updated_at):
    """Kết thúc do không lấy được hàng (A1). Không tạo nhiệm vụ mới; mã vận đơn + lịch sử giữ nguyên."""
    return _staff_decision(staff, shipment_id, reason, expected_updated_at, ShipmentAction.ABANDON_PICKUP,
                           NotificationKind.PICKUP_ABANDONED, PICKUP_ABANDONED_TITLE)


# ---------------------------------------------------------------- Spec 007: UC06.6, UC04.12 (phía Nhân viên)

def _holder_value(shipment):
    """Người / nơi đang giữ hàng, ghi vào changes của lịch sử."""
    if shipment.holder_type == HolderType.SHIPPER:
        return _person(shipment.holder_shipper)
    return {"name": HolderType(shipment.holder_type).label}


def _require_attempts_left(shipment):
    """D8: đủ 3 lần giao thực tế → chỉ được hoàn (UC06.6 E1, UC04.12 E1). Bảng trạng thái không biết số lần."""
    if not has_delivery_attempts_left(shipment):
        raise BusinessError(ErrorCode.LIMIT_REACHED, DELIVERY_LIMIT_MESSAGE.format(
            count=shipment.delivery_attempts, max=MAX_DELIVERY_ATTEMPTS))


def assign_delivery(staff, shipment_id, shipper_id, expected_updated_at):
    """UC06.6: tạo nhiệm vụ giao lần N (N = số lần đã giao + 1), đơn Đang giao hàng, Shipper giữ hàng.

    - Lần đầu từ Đã nhập điểm tập kết (BR1); giao lại từ Chờ giao lại — theo bảng trạng thái.
    - Không tăng số lần (chỉ tăng khi Shipper ghi kết quả).
    - D7: hàng đang ở Shipper X (giao lại) → chỉ phân công X; người khác cần đổi Shipper (spec 009, UC06.6 A2).
    - Xác nhận "Shipper đã nhận hàng" (bước 3–4) kiểm ở serializer.
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        if _resend_of_assignment(shipment, TaskType.DELIVERY, shipper_id):
            return shipment
        rule = _check(staff, shipment, ShipmentAction.ASSIGN_DELIVERY, expected_updated_at)
        _require_attempts_left(shipment)
        if shipment.holder_type == HolderType.SHIPPER and shipment.holder_shipper_id != shipper_id:
            raise BusinessError(ErrorCode.CONFLICT, HOLDER_ONLY_MESSAGE.format(name=shipment.holder_shipper.full_name))
        shipper = _lock_available_shipper(shipper_id)
        attempt = shipment.delivery_attempts + 1
        task = _create_task(shipment, TaskType.DELIVERY, shipper, staff, attempt_no=attempt)

        previous, previous_holder = shipment.status, _holder_value(shipment)
        shipment.status = rule.target
        shipment.holder_type = HolderType.SHIPPER
        shipment.holder_shipper = shipper
        shipment.save(update_fields=["status", "holder_type", "holder_shipper", "updated_at"])
        changes = {"shipper": {"from": None, "to": _person(shipper)}, "attempt_no": {"from": None, "to": attempt}}
        if previous_holder != _person(shipper):  # giao lại bằng người đang giữ: người giữ không đổi
            changes["holder"] = {"from": previous_holder, "to": _person(shipper)}
        _record(shipment, ShipmentAction.ASSIGN_DELIVERY, previous, staff, task=task, changes=changes)

        code = shipment.display_code
        notify(
            shipper, NotificationKind.TASK_ASSIGNED, DELIVERY_TASK_ASSIGNED_TITLE.format(code=code),
            DELIVERY_TASK_ASSIGNED_BODY.format(receiver=shipment.receiver_name, address=shipment.delivery_address,
                                               ward=shipment.delivery_ward.name, attempt=attempt,
                                               max=MAX_DELIVERY_ATTEMPTS),
            payload={"shipment_id": shipment.pk, "task_id": task.pk},
        )
        notify(
            shipment.shop, NotificationKind.OUT_FOR_DELIVERY, OUT_FOR_DELIVERY_TITLE.format(code=code),
            OUT_FOR_DELIVERY_BODY.format(name=shipper.full_name, attempt=attempt, max=MAX_DELIVERY_ATTEMPTS),
            payload={"shipment_id": shipment.pk},
        )
    return shipment


def decide_redelivery(staff, shipment_id, reason, expected_updated_at):
    """UC04.12: giao lại khi số lần < 3 → Chờ giao lại; phân công tiếp qua UC06.6. Lịch sử giữ nguyên."""
    return _staff_decision(staff, shipment_id, reason, expected_updated_at, ShipmentAction.DECIDE_REDELIVERY,
                           NotificationKind.REDELIVERY_SCHEDULED, REDELIVERY_SCHEDULED_TITLE,
                           guard=_require_attempts_left)


def decide_return(staff, shipment_id, reason, expected_updated_at):
    """UC04.12 A1: hoàn sớm (mọi lần) hoặc bắt buộc ở lần 3 → Chờ xử lý hoàn. Không tự tạo nhiệm vụ hoàn (BR2)."""
    return _staff_decision(staff, shipment_id, reason, expected_updated_at, ShipmentAction.DECIDE_RETURN,
                           NotificationKind.RETURN_DECIDED, RETURN_DECIDED_TITLE)


# ---------------------------------------------------------------- Spec 008: hoàn hàng (phía Nhân viên)

def _require_guard(shipment, action, message):
    """Điều kiện phụ ở shipments/rules.py (cùng bảng quyết định nút hiển thị) — sai thì INVALID_TRANSITION rõ nghĩa."""
    if not guard_allows(shipment, action):
        raise BusinessError(ErrorCode.INVALID_TRANSITION, message)


def assign_return(staff, shipment_id, shipper_id, expected_updated_at):
    """UC06.7: tạo nhiệm vụ đưa hàng hoàn về điểm tập kết; đơn Đang hoàn; báo Shipper.

    - Hàng phải đang ở Shipper (D3); hàng đã ở điểm tập kết → không tạo chuyến hoàn thừa (A1.2, A1.3).
    - Chỉ Shipper đang giữ hàng (đổi người ở spec 009 — A1.1); không cần xác nhận bàn giao (người đó giữ sẵn).
    - Không đặt Đã hoàn về Shop (BR1).
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        if _resend_of_assignment(shipment, TaskType.RETURN, shipper_id):
            return shipment
        rule = _check(staff, shipment, ShipmentAction.ASSIGN_RETURN, expected_updated_at)
        _require_guard(shipment, ShipmentAction.ASSIGN_RETURN, RETURN_ALREADY_AT_HUB_MESSAGE)
        if shipment.holder_shipper_id != shipper_id:
            raise BusinessError(ErrorCode.CONFLICT, HOLDER_ONLY_MESSAGE.format(name=shipment.holder_shipper.full_name))
        shipper = _lock_available_shipper(shipper_id)
        task = _create_task(shipment, TaskType.RETURN, shipper, staff)

        previous = shipment.status
        shipment.status = rule.target
        shipment.save(update_fields=["status", "updated_at"])
        _record(shipment, ShipmentAction.ASSIGN_RETURN, previous, staff, task=task,
                changes={"shipper": {"from": None, "to": _person(shipper)}})
        hub = settings.HUB
        notify(
            shipper, NotificationKind.TASK_ASSIGNED, RETURN_TASK_ASSIGNED_TITLE.format(code=shipment.display_code),
            RETURN_TASK_ASSIGNED_BODY.format(hub=hub["name"], address=hub["address"]),
            payload={"shipment_id": shipment.pk, "task_id": task.pk},
        )
    return shipment


def receive_return(staff, shipment_id, discrepancy_note, expected_updated_at):
    """UC04.9 bước 4–7 (và UC06.7 A1.2): Nhân viên nhận hàng hoàn thực tế tại điểm tập kết.

    Ghi bàn giao (người giao / nhận / thời gian / sai lệch), đóng nhiệm vụ hoàn (Nhân viên ghi kết quả — spec 001),
    đơn Chờ Shop đến lấy, hàng ở điểm tập kết, báo Shop đến nhận. Được làm cả khi Shipper chưa báo bàn giao (D5).
    Đã tiếp nhận rồi → trả hiện tại, không ghi bàn giao thứ hai.
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        if (shipment.status == ShipmentStatus.AWAITING_SHOP_PICKUP
                and _last_event_is(shipment, ShipmentAction.RECEIVE_RETURN, staff)):
            return shipment
        rule = _check(staff, shipment, ShipmentAction.RECEIVE_RETURN, expected_updated_at)
        _require_guard(shipment, ShipmentAction.RECEIVE_RETURN, RETURN_NEEDS_TRIP_MESSAGE.format(
            name=shipment.holder_shipper.full_name if shipment.holder_shipper else ""))
        task = _open_task(shipment)  # Đang hoàn → nhiệm vụ hoàn mở; A1.2 → không có
        if task is not None:
            if task.type != TaskType.RETURN:
                raise BusinessError(ErrorCode.INVALID_TRANSITION, TASK_CLOSED_MESSAGE)
            task_rule = resolve_transition(TASK_TRANSITIONS, TaskAction.TASK_SUCCEED, task.status, staff.role)
            _close_task(task, task_rule.target, staff)
        from_shipper, previous_holder = shipment.holder_shipper, _holder_value(shipment)
        Handover.objects.create(
            shipment=shipment, task=task, kind=HandoverKind.RETURN_INTAKE, from_shipper=from_shipper,
            received_by=staff, received_at=timezone.now(), discrepancy_note=discrepancy_note,
        )
        previous = shipment.status
        shipment.status = rule.target
        shipment.holder_type = HolderType.HUB
        shipment.holder_shipper = None
        shipment.save(update_fields=["status", "holder_type", "holder_shipper", "updated_at"])
        changes = {"holder": {"from": previous_holder, "to": {"name": HolderType.HUB.label}}}
        if discrepancy_note:
            changes["discrepancy_note"] = {"from": None, "to": discrepancy_note}
        _record(shipment, ShipmentAction.RECEIVE_RETURN, previous, staff, task=task, changes=changes)
        hub = settings.HUB
        notify(shipment.shop, NotificationKind.RETURN_AT_HUB, RETURN_AT_HUB_TITLE.format(code=shipment.display_code),
               RETURN_AT_HUB_BODY.format(hub=hub["name"], address=hub["address"], phone=hub["phone"]),
               payload={"shipment_id": shipment.pk})
    return shipment


def report_return_issue(staff, shipment_id, reason, expected_updated_at):
    """UC04.9 E1: sai mã / thiếu kiện / sai tình trạng — ghi rõ sai lệch, CHƯA tiếp nhận.

    Không đổi trạng thái, nhiệm vụ hoàn vẫn mở; ghi mốc lịch sử và tăng phiên bản đơn (NV khác đang xem bản cũ phải
    tải lại). Gửi lại đúng ghi chú vừa ghi → trả hiện tại (không ghi trùng).
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        last = shipment.events.order_by("-created_at", "-id").first()
        if (last is not None and last.action == ShipmentAction.REPORT_RETURN_ISSUE and last.actor_id == staff.pk
                and last.reason == reason):
            return shipment
        _check(staff, shipment, ShipmentAction.REPORT_RETURN_ISSUE, expected_updated_at)
        shipment.save(update_fields=["updated_at"])
        _record(shipment, ShipmentAction.REPORT_RETURN_ISSUE, shipment.status, staff, task=_open_task(shipment),
                reason=reason)
    return shipment


def confirm_shop_received(staff, shipment_id, receiver_name, note, expected_updated_at):
    """UC04.11: Shop (hoặc người được ủy quyền) đã nhận lại hàng tại điểm tập kết → Đã hoàn về Shop.

    Lưu người bàn giao (Nhân viên), người nhận, thời gian; hàng ở Shop; báo Shop. Việc kiểm người nhận thuộc Shop
    (bước 3) xác nhận ở serializer. Đã hoàn tất → trả hiện tại, không ghi thêm (E1).
    """
    with transaction.atomic():
        shipment = lock_visible(staff, shipment_id)
        if (shipment.status == ShipmentStatus.RETURNED_TO_SHOP
                and _last_event_is(shipment, ShipmentAction.CONFIRM_SHOP_RECEIVED, staff)):
            return shipment
        rule = _check(staff, shipment, ShipmentAction.CONFIRM_SHOP_RECEIVED, expected_updated_at)
        Handover.objects.create(
            shipment=shipment, kind=HandoverKind.SHOP_PICKUP, received_by=staff, received_at=timezone.now(),
            receiver_name=receiver_name, discrepancy_note=note,
        )
        previous = shipment.status
        shipment.status = rule.target
        shipment.holder_type = HolderType.SHOP
        shipment.holder_shipper = None
        shipment.save(update_fields=["status", "holder_type", "holder_shipper", "updated_at"])
        _record(shipment, ShipmentAction.CONFIRM_SHOP_RECEIVED, previous, staff, reason=note, changes={
            "holder": {"from": {"name": HolderType.HUB.label}, "to": {"name": receiver_name}},
        })
        notify(shipment.shop, NotificationKind.RETURN_COMPLETED,
               RETURN_COMPLETED_TITLE.format(code=shipment.display_code), RETURN_COMPLETED_BODY.format(name=receiver_name),
               payload={"shipment_id": shipment.pk})
    return shipment


# ---------------------------------------------------------------- D9 Khóa Shipper còn nhiệm vụ mở

def flag_open_tasks_of_locked_shipper(actor, user):
    """Hook của accounts.lock_account (chạy TRONG transaction khóa, dòng user đã khóa).

    Nhiệm vụ mở của Shipper bị khóa: bật needs_attention, báo mọi Nhân viên đang hoạt động. Không tự đóng
    nhiệm vụ — đổi người ở UC06.8 (spec 009).
    """
    if user.role != UserRole.SHIPPER:
        return
    task_ids = list(Task.objects.select_for_update().filter(shipper=user, status__in=OPEN_TASK_STATUSES)
                    .values_list("pk", flat=True))
    if not task_ids:
        return
    Task.objects.filter(pk__in=task_ids).update(needs_attention=True, updated_at=timezone.now())
    notify(
        list(_active_staff()), NotificationKind.ACCOUNT_LOCKED_TASKS,
        LOCKED_TASKS_TITLE.format(name=user.full_name, count=len(task_ids)), LOCKED_TASKS_BODY,
        payload={"shipper_id": user.pk, "task_ids": task_ids},
    )


# ---------------------------------------------------------------- UC04.2 / UC04.3 Shipper ghi kết quả lấy hàng

def _lock_own_task(shipper, task_id):
    """Khóa ĐƠN rồi NHIỆM VỤ (cùng thứ tự với thao tác Nhân viên). Nhiệm vụ không phải của mình → 404 (UC04.1 E1)."""
    shipment_id = tasks_visible_to(shipper).filter(pk=task_id).values_list("shipment_id", flat=True).first()
    if shipment_id is None:
        raise BusinessError(ErrorCode.NOT_FOUND)
    shipment = Shipment.objects.select_for_update().get(pk=shipment_id)
    task = tasks_visible_to(shipper).select_for_update().filter(pk=task_id).first()
    if task is None:
        raise BusinessError(ErrorCode.NOT_FOUND)
    return shipment, task


def _already_recorded(task, outcome, shipper):
    """Gửi lại (UC04.2 BR2): nhiệm vụ đã có đúng kết quả này do chính người này ghi → trả hiện tại."""
    result = TaskResult.objects.filter(task=task).first()
    return task.status == outcome and result is not None and result.recorded_by_id == shipper.pk


def _resolve_own_task(task, shipment, shipper, task_type, task_action, shipment_action):
    """Bảng nhiệm vụ + bảng vận đơn. Nhiệm vụ không còn ACTIVE / sai loại → INVALID_TRANSITION rõ nghĩa."""
    if task.type != task_type:
        raise BusinessError(ErrorCode.INVALID_TRANSITION, TASK_CLOSED_MESSAGE)
    try:
        task_rule = resolve_transition(TASK_TRANSITIONS, task_action, task.status, shipper.role)
        ship_rule = resolve_transition(SHIPMENT_TRANSITIONS, shipment_action, shipment.status, shipper.role)
    except BusinessError as exc:
        if exc.code == ErrorCode.INVALID_TRANSITION:
            raise BusinessError(ErrorCode.INVALID_TRANSITION, TASK_CLOSED_MESSAGE) from None
        raise
    return task_rule, ship_rule


def _close_task(task, target, shipper, *, reason_code=None, note="", cod_expected=None, cod_collected=None):
    now = timezone.now()
    task.status = target
    task.closed_at = now
    task.save(update_fields=["status", "closed_at", "updated_at"])
    TaskResult.objects.create(task=task, outcome=target, reason_code=reason_code, note=note, recorded_by=shipper,
                              recorded_at=now, cod_expected=cod_expected, cod_collected=cod_collected)


def _reason_text(task_type, reason_code, note):
    """Lý do thất bại ghi vào lịch sử + thông báo: nhãn theo nhóm của loại nhiệm vụ (+ ghi chú)."""
    label = FAIL_REASONS_BY_TASK_TYPE[task_type](reason_code).label
    return FAIL_REASON_WITH_NOTE.format(reason=label, note=note) if note else label


def confirm_pickup(shipper, task_id):
    """UC04.2: đã nhận hàng thực tế → nhiệm vụ hoàn tất, đơn Đã lấy hàng, Shipper giữ hàng, báo Shop.

    Chưa phải Đã nhập điểm tập kết (BR1) — Nhân viên xác nhận ở UC04.10.
    """
    with transaction.atomic():
        shipment, task = _lock_own_task(shipper, task_id)
        if _already_recorded(task, TaskStatus.SUCCEEDED, shipper):
            return task
        task_rule, ship_rule = _resolve_own_task(task, shipment, shipper, TaskType.PICKUP, TaskAction.TASK_SUCCEED,
                                                 ShipmentAction.CONFIRM_PICKUP)
        _close_task(task, task_rule.target, shipper)
        previous = shipment.status
        shipment.status = ship_rule.target
        shipment.holder_type = HolderType.SHIPPER
        shipment.holder_shipper = shipper
        shipment.save(update_fields=["status", "holder_type", "holder_shipper", "updated_at"])
        _record(shipment, ShipmentAction.CONFIRM_PICKUP, previous, shipper, task=task,
                changes={"holder": {"from": {"name": HolderType.SHOP.label}, "to": _person(shipper)}})
        notify(shipment.shop, NotificationKind.PICKED_UP, PICKED_UP_TITLE.format(code=shipment.display_code),
               PICKED_UP_BODY.format(name=shipper.full_name), payload={"shipment_id": shipment.pk})
    return task


def fail_pickup(shipper, task_id, reason_code, note):
    """UC04.3: không nhận được hàng → nhiệm vụ thất bại, đơn Lấy hàng thất bại; hàng vẫn ở Shop (BR2).

    Báo Shop + mọi Nhân viên đang hoạt động (bước 7). Chỉ Nhân viên quyết định lấy lại / kết thúc (BR1).
    """
    with transaction.atomic():
        shipment, task = _lock_own_task(shipper, task_id)
        if _already_recorded(task, TaskStatus.FAILED, shipper):
            return task
        task_rule, ship_rule = _resolve_own_task(task, shipment, shipper, TaskType.PICKUP, TaskAction.TASK_FAIL,
                                                 ShipmentAction.FAIL_PICKUP)
        _close_task(task, task_rule.target, shipper, reason_code=reason_code, note=note)
        previous = shipment.status
        shipment.status = ship_rule.target
        shipment.save(update_fields=["status", "updated_at"])
        reason_text = _reason_text(task.type, reason_code, note)
        _record(shipment, ShipmentAction.FAIL_PICKUP, previous, shipper, task=task, reason=reason_text)
        notify([shipment.shop, *_active_staff()], NotificationKind.PICKUP_FAILED,
               PICKUP_FAILED_TITLE.format(code=shipment.display_code), REASON_BODY.format(reason=reason_text),
               payload={"shipment_id": shipment.pk})
    return task


# ---------------------------------------------------------------- Spec 007: UC04.5–04.7 Shipper ghi kết quả giao

def _check_cod(expected, collected):
    """UC04.7 bước 4, E1: thực thu phải bằng phải thu — báo rõ thiếu / thừa bao nhiêu, không thu một phần."""
    if collected == expected:
        return
    template = COD_SHORT_MESSAGE if collected < expected else COD_OVER_MESSAGE
    message = template.format(diff=format_vnd(abs(expected - collected)), expected=format_vnd(expected))
    raise BusinessError(ErrorCode.VALIDATION_ERROR, message, fields={"cod_collected": [message]})


def confirm_delivery(shipper, task_id, cod_collected):
    """UC04.5 + UC04.7: người nhận đã nhận hàng, COD thực thu = phải thu → Đã giao hàng.

    Kết quả + COD + thời gian + số thứ tự lần giao ghi cùng một transaction (bước 6). Số lần đã giao = lần của
    nhiệm vụ (gán, không cộng) → gửi lại không bao giờ cộng tiền hay tăng lần (BR2). COD lệch → không ghi gì.
    """
    with transaction.atomic():
        shipment, task = _lock_own_task(shipper, task_id)
        if _already_recorded(task, TaskStatus.SUCCEEDED, shipper):
            return task
        task_rule, ship_rule = _resolve_own_task(task, shipment, shipper, TaskType.DELIVERY, TaskAction.TASK_SUCCEED,
                                                 ShipmentAction.CONFIRM_DELIVERY)
        _check_cod(shipment.cod_amount, cod_collected)
        _close_task(task, task_rule.target, shipper, cod_expected=shipment.cod_amount, cod_collected=cod_collected)
        previous, previous_attempts = shipment.status, shipment.delivery_attempts
        shipment.status = ship_rule.target
        shipment.holder_type = HolderType.RECIPIENT
        shipment.holder_shipper = None
        shipment.delivery_attempts = task.attempt_no
        shipment.save(update_fields=["status", "holder_type", "holder_shipper", "delivery_attempts", "updated_at"])
        _record(shipment, ShipmentAction.CONFIRM_DELIVERY, previous, shipper, task=task, changes={
            "holder": {"from": _person(shipper), "to": {"name": HolderType.RECIPIENT.label}},
            "delivery_attempts": {"from": previous_attempts, "to": task.attempt_no},
            "cod_collected": {"from": None, "to": cod_collected},
        })
        body = DELIVERED_COD_BODY.format(amount=format_vnd(cod_collected)) if cod_collected else ""
        notify(shipment.shop, NotificationKind.DELIVERED, DELIVERED_TITLE.format(code=shipment.display_code), body,
               payload={"shipment_id": shipment.pk})
    return task


def fail_delivery(shipper, task_id, reason_code, note):
    """UC04.6: lần giao không thành công → số lần = lần của nhiệm vụ (tăng đúng một lần), đơn Giao hàng thất bại.

    Hàng vẫn ở Shipper (bước 7); báo Shop + mọi Nhân viên đang hoạt động; không tự tạo nhiệm vụ tiếp theo — Nhân viên
    quyết định giao lại / hoàn (UC04.12, BR2).
    """
    with transaction.atomic():
        shipment, task = _lock_own_task(shipper, task_id)
        if _already_recorded(task, TaskStatus.FAILED, shipper):
            return task
        task_rule, ship_rule = _resolve_own_task(task, shipment, shipper, TaskType.DELIVERY, TaskAction.TASK_FAIL,
                                                 ShipmentAction.FAIL_DELIVERY)
        _close_task(task, task_rule.target, shipper, reason_code=reason_code, note=note)
        previous, previous_attempts = shipment.status, shipment.delivery_attempts
        shipment.status = ship_rule.target
        shipment.delivery_attempts = task.attempt_no
        shipment.save(update_fields=["status", "delivery_attempts", "updated_at"])
        reason_text = _reason_text(task.type, reason_code, note)
        _record(shipment, ShipmentAction.FAIL_DELIVERY, previous, shipper, task=task, reason=reason_text,
                changes={"delivery_attempts": {"from": previous_attempts, "to": task.attempt_no}})
        notify([shipment.shop, *_active_staff()], NotificationKind.DELIVERY_FAILED,
               DELIVERY_FAILED_TITLE.format(code=shipment.display_code, attempt=task.attempt_no,
                                            max=MAX_DELIVERY_ATTEMPTS),
               REASON_BODY.format(reason=reason_text), payload={"shipment_id": shipment.pk})
    return task


# ---------------------------------------------------------------- Spec 008: UC04.9 bước 1–3 Shipper báo bàn giao

def report_return_handover(shipper, task_id):
    """Shipper đã đưa hàng hoàn về điểm tập kết và đề nghị tiếp nhận (D4).

    Chỉ ghi `handover_reported_at` + mốc lịch sử + báo mọi Nhân viên đang hoạt động; nhiệm vụ vẫn mở, đơn vẫn Đang hoàn
    (A1) — Nhân viên mới xác nhận tiếp nhận (BR1). Không tăng phiên bản đơn: NV tiếp nhận không phụ thuộc lần báo này
    (D5). Đã báo rồi → trả hiện tại.
    """
    with transaction.atomic():
        shipment, task = _lock_own_task(shipper, task_id)
        if task.type == TaskType.RETURN and task.handover_reported_at is not None:
            return task
        if task.type != TaskType.RETURN or not task.is_open:
            raise BusinessError(ErrorCode.INVALID_TRANSITION, TASK_CLOSED_MESSAGE)
        try:
            resolve_transition(SHIPMENT_TRANSITIONS, ShipmentAction.REPORT_RETURN_HANDOVER, shipment.status,
                               shipper.role)
        except BusinessError as exc:
            if exc.code == ErrorCode.INVALID_TRANSITION:
                raise BusinessError(ErrorCode.INVALID_TRANSITION, TASK_CLOSED_MESSAGE) from None
            raise
        task.handover_reported_at = timezone.now()
        task.save(update_fields=["handover_reported_at", "updated_at"])
        _record(shipment, ShipmentAction.REPORT_RETURN_HANDOVER, shipment.status, shipper, task=task)
        notify(list(_active_staff()), NotificationKind.RETURN_HANDOVER_REPORTED,
               RETURN_HANDOVER_REPORTED_TITLE.format(name=shipper.full_name, code=shipment.display_code),
               RETURN_HANDOVER_REPORTED_BODY, payload={"shipment_id": shipment.pk})
    return task
