"""Spec 006 Phase 1: ràng buộc DB của nhiệm vụ / kết quả / bàn giao (lớp chặn cuối, spec 001 mục 3.6 điểm 4)."""
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.dispatch.constants import (
    OPEN_TASK_STATUSES,
    TERMINAL_TASK_STATUSES,
    HandoverKind,
    PickupFailReason,
    TaskStatus,
    TaskType,
)
from apps.dispatch.models import Handover, Task, TaskResult
from apps.shipments.constants import ShipmentAction, ShipmentStatus
from apps.shipments.models import ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward


class Base(TestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.shipment = make_shipment(self.shop, make_ward())

    def task(self, **extra):
        data = {"shipment": self.shipment, "type": TaskType.PICKUP, "shipper": self.shipper,
                "assigned_by": self.admin, **extra}
        return Task.objects.create(**data)

    def assert_rejected(self, fn):
        with self.assertRaises(IntegrityError), transaction.atomic():
            fn()


class TaskConstraintTests(Base):
    def test_defaults(self):
        task = self.task()
        self.assertEqual((task.status, task.needs_attention, task.closed_at), (TaskStatus.ACTIVE, False, None))
        self.assertTrue(task.is_open)

    def test_one_open_task_per_shipment(self):
        """D1: lớp chặn cuối cho 'không phân công trùng' — kể cả khi service có lỗi hay hai yêu cầu song song."""
        self.task()
        self.assert_rejected(lambda: self.task())
        self.assert_rejected(lambda: self.task(status=TaskStatus.PENDING_SWAP_HANDOVER))
        self.assertEqual(set(OPEN_TASK_STATUSES), {TaskStatus.ACTIVE, TaskStatus.PENDING_SWAP_HANDOVER})

    def test_closed_tasks_do_not_block_new_one(self):
        """Lấy lại (UC04.13) tạo nhiệm vụ mới khi nhiệm vụ cũ đã đóng — giữ lịch sử lần trước (UC06.5 BR1)."""
        for status in sorted(TERMINAL_TASK_STATUSES):
            self.task(status=status, closed_at=timezone.now())
        self.task()  # không lỗi
        self.assertEqual(self.shipment.tasks.count(), len(TERMINAL_TASK_STATUSES) + 1)

    def test_other_shipment_unaffected(self):
        self.task()
        Task.objects.create(shipment=make_shipment(self.shop, self.shipment.pickup_ward), type=TaskType.PICKUP,
                            shipper=self.shipper, assigned_by=self.admin)

    def test_closed_at_matches_status(self):
        self.assert_rejected(lambda: self.task(status=TaskStatus.SUCCEEDED))  # kết thúc mà thiếu closed_at
        self.assert_rejected(lambda: self.task(closed_at=timezone.now()))  # còn mở mà có closed_at

    def test_enums_and_attempt_only_for_delivery(self):
        self.assert_rejected(lambda: self.task(type="FLY"))
        self.assert_rejected(lambda: self.task(status="LOST"))
        self.assert_rejected(lambda: self.task(attempt_no=1))  # PICKUP không có lần giao
        self.task(type=TaskType.DELIVERY, attempt_no=1)  # chi tiết khoảng 1..3: test_delivery_models.py


class TaskResultConstraintTests(Base):
    def setUp(self):
        super().setUp()
        self.closed = self.task(status=TaskStatus.FAILED, closed_at=timezone.now())

    def result(self, **extra):
        data = {"task": self.closed, "outcome": TaskStatus.FAILED, "reason_code": PickupFailReason.SHOP_ABSENT,
                "recorded_by": self.shipper, **extra}
        return TaskResult.objects.create(**data)

    def test_one_result_per_task(self):
        self.result()
        self.assert_rejected(lambda: self.result())

    def test_reason_required_iff_failed(self):
        self.assert_rejected(lambda: self.result(reason_code=None))
        self.assert_rejected(lambda: self.result(outcome=TaskStatus.SUCCEEDED))  # thành công mà có lý do
        self.assert_rejected(lambda: self.result(outcome=TaskStatus.REPLACED, reason_code=None))  # không phải kết quả
        self.result(outcome=TaskStatus.SUCCEEDED, reason_code=None)


class HandoverAndEventTests(Base):
    def test_handover_kind_and_optional_task(self):
        Handover.objects.create(shipment=self.shipment, kind=HandoverKind.HUB_INTAKE, received_by=self.admin)
        self.assert_rejected(lambda: Handover.objects.create(shipment=self.shipment, kind="X",
                                                             received_by=self.admin))

    def test_event_links_task_and_task_cannot_be_deleted(self):
        task = self.task()
        event = ShipmentEvent.objects.create(shipment=self.shipment, action=ShipmentAction.ASSIGN_PICKUP,
                                             from_status=ShipmentStatus.AWAITING_PICKUP,
                                             to_status=ShipmentStatus.PICKUP_ASSIGNED, actor=self.admin, task=task)
        self.assertEqual(list(task.events.all()), [event])
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            task.delete()  # lịch sử không bao giờ mất nhiệm vụ nó tham chiếu
        with self.assertRaises(ProtectedError):
            self.shipper.delete()  # Shipper có nhiệm vụ: khóa tài khoản, không xóa (BR1 spec 003)
