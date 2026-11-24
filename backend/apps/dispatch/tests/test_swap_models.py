"""Spec 009 Phase 1: ràng buộc DB `swap_candidate`, mã mới, điều kiện hiển thị nút đổi Shipper."""
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.dispatch.constants import HandoverKind, TaskStatus, TaskType
from apps.dispatch.models import Task
from apps.notifications.constants import NotificationKind
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment
from apps.shipments.rules import shipment_allowed_actions
from apps.shipments.tests.factories import make_shipment, make_user, make_ward

A = ShipmentAction
S = ShipmentStatus
ADMIN, SHIPPER = UserRole.ADMIN, UserRole.SHIPPER


class Base(TestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.other = make_user("sp_b", "0900000006", UserRole.SHIPPER)
        self.shipment = make_shipment(self.shop, make_ward())

    def at(self, status, holder=HolderType.SHOP, holder_shipper=None):
        Shipment.objects.filter(pk=self.shipment.pk).update(status=status, holder_type=holder,
                                                            holder_shipper=holder_shipper)
        return Shipment.objects.get(pk=self.shipment.pk)

    def task(self, **extra):
        data = {"shipment": self.shipment, "type": TaskType.DELIVERY, "attempt_no": 1, "shipper": self.shipper,
                "assigned_by": self.admin, **extra}
        return Task.objects.create(**data)

    def assert_rejected(self, fn):
        with self.assertRaises(IntegrityError), transaction.atomic():
            fn()


class SwapCandidateConstraintTests(Base):
    def test_candidate_only_while_pending(self):
        """D1 (A1.2): người dự kiến có ⇔ Chờ bàn giao đổi Shipper."""
        self.assert_rejected(lambda: self.task(status=TaskStatus.PENDING_SWAP_HANDOVER))  # chờ mà thiếu người
        self.assert_rejected(lambda: self.task(swap_candidate=self.other))  # ACTIVE mà có người dự kiến
        self.assert_rejected(lambda: self.task(status=TaskStatus.REPLACED, closed_at=timezone.now(),
                                               swap_candidate=self.other))
        task = self.task(status=TaskStatus.PENDING_SWAP_HANDOVER, swap_candidate=self.other)
        self.assertEqual(task.swap_candidate, self.other)


class CatalogTests(TestCase):
    def test_new_codes(self):
        for code in ("SWAP_SHIPPER", "CONFIRM_SWAP_HANDOVER", "REPORT_SWAP_ISSUE", "REPORT_SWAP_HANDOVER",
                     "RECALL_TO_HUB"):
            self.assertIn(code, ShipmentAction.values)
        self.assertIn("REASSIGN_INTAKE", HandoverKind.values)
        for code in ("SWAP_HANDOVER_REQUIRED", "SWAP_HANDOVER_REPORTED"):
            self.assertIn(code, NotificationKind.values)


class GuardTests(Base):
    """D3, D4, D6, D9: nút theo nhiệm vụ đang mở / nơi giữ hàng — không hiện nút sai cho mọi đơn đang giao."""

    def staff_actions(self):
        return shipment_allowed_actions(Shipment.objects.get(pk=self.shipment.pk), ADMIN)

    def test_swap_only_with_open_pickup_or_delivery_task(self):
        self.at(S.PICKUP_ASSIGNED)
        self.assertNotIn(A.SWAP_SHIPPER, self.staff_actions())  # chưa có nhiệm vụ mở
        self.task(type=TaskType.PICKUP, attempt_no=None)
        self.assertEqual(self.staff_actions(), [A.SWAP_SHIPPER])

    def test_delivery_active_vs_pending(self):
        self.at(S.OUT_FOR_DELIVERY, HolderType.SHIPPER, self.shipper)
        task = self.task()
        self.assertEqual(self.staff_actions(), [A.SWAP_SHIPPER])
        Task.objects.filter(pk=task.pk).update(status=TaskStatus.PENDING_SWAP_HANDOVER, swap_candidate=self.other)
        self.assertEqual(self.staff_actions(), [A.CONFIRM_SWAP_HANDOVER, A.REPORT_SWAP_ISSUE, A.SWAP_SHIPPER])
        shipper_actions = shipment_allowed_actions(Shipment.objects.get(pk=self.shipment.pk), SHIPPER)
        self.assertIn(A.REPORT_SWAP_HANDOVER, shipper_actions)

    def test_shipper_report_swap_hidden_without_pending(self):
        self.at(S.OUT_FOR_DELIVERY, HolderType.SHIPPER, self.shipper)
        self.task()
        actions = shipment_allowed_actions(Shipment.objects.get(pk=self.shipment.pk), SHIPPER)
        self.assertEqual(actions, [A.CONFIRM_DELIVERY, A.FAIL_DELIVERY])

    def test_recall_only_when_goods_with_shipper_and_no_open_task(self):
        self.at(S.AWAITING_REDELIVERY, HolderType.SHIPPER, self.shipper)
        self.assertIn(A.RECALL_TO_HUB, self.staff_actions())
        self.at(S.AWAITING_REDELIVERY, HolderType.HUB)
        self.assertNotIn(A.RECALL_TO_HUB, self.staff_actions())
        self.at(S.AWAITING_RETURN, HolderType.SHIPPER, self.shipper)
        self.assertIn(A.RECALL_TO_HUB, self.staff_actions())

    def test_return_task_not_swappable(self):
        """D3: nhiệm vụ hoàn không đổi người."""
        self.at(S.RETURNING, HolderType.SHIPPER, self.shipper)
        self.task(type=TaskType.RETURN, attempt_no=None)
        self.assertNotIn(A.SWAP_SHIPPER, self.staff_actions())


class ShipperTaskButtonsTests(Base):
    """D4: người cũ đang chờ bàn giao mất Giao thành công / thất bại, chỉ còn báo đã đưa về (một lần)."""

    def setUp(self):
        super().setUp()
        self.at(S.OUT_FOR_DELIVERY, HolderType.SHIPPER, self.shipper)
        self.delivery = self.task()
        self.client.force_login(self.shipper)

    def actions(self):
        from django.urls import reverse

        return self.client.get(reverse("task-detail", args=[self.delivery.pk])).json()["allowed_actions"]

    def test_active_task_keeps_delivery_actions(self):
        self.assertEqual(self.actions(), [A.CONFIRM_DELIVERY, A.FAIL_DELIVERY])

    def test_pending_task_only_reports_handover_once(self):
        Task.objects.filter(pk=self.delivery.pk).update(status=TaskStatus.PENDING_SWAP_HANDOVER,
                                                       swap_candidate=self.other)
        self.assertEqual(self.actions(), [A.REPORT_SWAP_HANDOVER])
        Task.objects.filter(pk=self.delivery.pk).update(handover_reported_at=timezone.now())
        self.assertEqual(self.actions(), [])

