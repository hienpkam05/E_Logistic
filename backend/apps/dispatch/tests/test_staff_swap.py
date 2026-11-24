"""Spec 009 Phase 2: API Nhân viên, giao dịch, gửi lại và bàn giao đổi Shipper."""
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.services import lock_account
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import HandoverKind, TaskStatus, TaskType
from apps.dispatch.models import Handover, Task, TaskResult
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward

A, S, T = ShipmentAction, ShipmentStatus, TaskStatus
HUB = {"name": "Điểm thử", "address": "12 Xuân Thủy", "phone": "0241234567"}


def swap_fixture(obj):
    obj.shop = make_user("shop_a", "0900000001")
    obj.admin = make_user("nv_a", "0900000002", UserRole.ADMIN)
    obj.admin_2 = make_user("nv_b", "0900000003", UserRole.ADMIN)
    obj.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
    obj.other = make_user("sp_b", "0900000005", UserRole.SHIPPER)
    obj.third = make_user("sp_c", "0900000006", UserRole.SHIPPER)
    obj.shipment = make_shipment(obj.shop, make_ward())


@override_settings(HUB=HUB)
class StaffSwapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        swap_fixture(cls)

    def setUp(self):
        self.client.force_login(self.admin)

    def fresh(self):
        return Shipment.objects.get(pk=self.shipment.pk)

    def prepare_task(self, task_type=TaskType.DELIVERY, attempts=1):
        pickup = task_type == TaskType.PICKUP
        Shipment.objects.filter(pk=self.shipment.pk).update(
            status=S.PICKUP_ASSIGNED if pickup else S.OUT_FOR_DELIVERY,
            holder_type=HolderType.SHOP if pickup else HolderType.SHIPPER,
            holder_shipper=None if pickup else self.shipper, delivery_attempts=0 if pickup else attempts,
        )
        return Task.objects.create(shipment=self.shipment, type=task_type, shipper=self.shipper,
                                   assigned_by=self.admin, attempt_no=None if pickup else attempts + 1)

    def post_action(self, name, body=None, version=None):
        return self.client.post(reverse("shipment-" + name, args=[self.shipment.pk]),
                                {"updated_at": version or self.fresh().updated_at.isoformat(), **(body or {})},
                                content_type="application/json")

    def swap(self, user=None, reason="Nghỉ đột xuất", **kwargs):
        return self.post_action("swap-shipper", {"shipper_id": (user or self.other).pk, "reason": reason}, **kwargs)

    def confirm(self, **kwargs):
        return self.post_action("confirm-swap-handover", {"handed_over": True, "discrepancy_note": "Đủ hàng"}, **kwargs)

    def detail(self):
        return self.client.get(reverse("shipment-detail", args=[self.shipment.pk]))

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def error(self, response, status=409, code=ErrorCode.INVALID_TRANSITION):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)
        return response.json()["error"]

    def test_pickup_replaces_immediately_and_resend_is_noop(self):
        old = self.prepare_task(TaskType.PICKUP)
        lock_account(self.admin, self.shipper.pk)
        Notification.objects.all().delete()
        version = self.fresh().updated_at.isoformat()
        body = self.ok(self.swap(version=version))
        self.ok(self.swap(version=version))
        old.refresh_from_db()
        new = Task.objects.get(status=T.ACTIVE)
        self.assertEqual((old.status, old.replaced_by_id, old.needs_attention), (T.REPLACED, new.pk, False))
        self.assertIsNotNone(old.closed_at)
        self.assertEqual((new.type, new.shipper, new.attempt_no, new.needs_attention),
                         (TaskType.PICKUP, self.other, None, False))
        self.assertEqual((body["status"], body["holder_type"], body["delivery_attempts"]),
                         (S.PICKUP_ASSIGNED, HolderType.SHOP, 0))
        self.assertFalse(TaskResult.objects.exists())
        self.assertFalse(Handover.objects.exists())
        self.assertEqual(ShipmentEvent.objects.get().reason, "Nghỉ đột xuất")
        self.assertCountEqual(Notification.objects.values_list("recipient_id", "kind"),
                              [(self.shipper.pk, NotificationKind.TASK_REPLACED),
                               (self.other.pk, NotificationKind.TASK_ASSIGNED)])
        summary = next(t for t in body["tasks"] if t["id"] == old.pk)
        self.assertEqual(summary["replaced_by"], {"id": new.pk, "shipper": {"id": self.other.pk,
                                      "username": self.other.username, "full_name": self.other.full_name}})

    def test_delivery_waits_and_changes_candidate_without_granting_task(self):
        old = self.prepare_task()
        version = self.fresh().updated_at.isoformat()
        body = self.ok(self.swap(version=version))
        self.ok(self.swap(version=version))
        self.assertNotEqual(body["updated_at"], version)
        old.refresh_from_db()
        self.assertEqual((old.status, old.swap_candidate_id, old.closed_at), (T.PENDING_SWAP_HANDOVER, self.other.pk, None))
        self.assertEqual(body["tasks"][0]["swap_candidate"]["id"], self.other.pk)
        self.assertEqual((self.fresh().holder_shipper, self.fresh().delivery_attempts), (self.shipper, 1))
        note = Notification.objects.get()
        self.assertEqual((note.recipient, note.kind), (self.shipper, NotificationKind.SWAP_HANDOVER_REQUIRED))
        self.assertIn(HUB["address"], note.body)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("task-detail", args=[old.pk])).status_code, 404)
        self.client.force_login(self.admin)
        self.ok(self.swap(self.third))
        old.refresh_from_db()
        self.assertEqual(old.swap_candidate_id, self.third.pk)
        self.assertEqual((Task.objects.count(), Notification.objects.count(), ShipmentEvent.objects.count()), (1, 1, 2))
        event = ShipmentEvent.objects.latest("id")
        self.assertEqual(event.changes["swap_candidate"]["from"]["id"], self.other.pk)
        self.assertIn(A.CONFIRM_SWAP_HANDOVER, self.ok(self.detail())["allowed_actions"])

    def test_confirm_preserves_attempt_and_records_handover_even_if_old_locked(self):
        old = self.prepare_task(attempts=2)
        self.ok(self.swap())
        lock_account(self.admin, self.shipper.pk)
        Notification.objects.all().delete()
        version = self.fresh().updated_at.isoformat()
        body = self.ok(self.confirm(version=version))
        self.ok(self.confirm(version=version))
        old.refresh_from_db()
        new = Task.objects.get(status=T.ACTIVE)
        self.assertEqual((old.status, old.swap_candidate, old.replaced_by_id, old.needs_attention),
                         (T.REPLACED, None, new.pk, False))
        self.assertEqual((new.shipper, new.type, new.attempt_no, new.needs_attention),
                         (self.other, TaskType.DELIVERY, 3, False))
        self.assertEqual((body["status"], body["delivery_attempts"], body["holder_shipper"]["id"], body["holder_locked"]),
                         (S.OUT_FOR_DELIVERY, 2, self.other.pk, False))
        handover = Handover.objects.get()
        self.assertEqual((handover.kind, handover.from_shipper, handover.received_by, handover.task),
                         (HandoverKind.REASSIGN_INTAKE, self.shipper, self.admin, old))
        self.assertEqual(handover.discrepancy_note, "Đủ hàng")
        self.assertIsNotNone(handover.received_at)
        self.assertFalse(TaskResult.objects.exists())
        self.assertCountEqual(Notification.objects.values_list("recipient_id", "kind"),
                              [(self.shipper.pk, NotificationKind.TASK_REPLACED),
                               (self.other.pk, NotificationKind.TASK_ASSIGNED)])
        event = ShipmentEvent.objects.get(action=A.CONFIRM_SWAP_HANDOVER)
        old_notice = Notification.objects.get(recipient=self.shipper, kind=NotificationKind.TASK_REPLACED)
        self.assertIn("Nghỉ đột xuất", old_notice.body)
        self.assertNotIn("Đủ hàng", old_notice.body)  # ghi chú nhận hàng không phải lý do đổi người
        self.assertEqual((event.from_status, event.to_status, event.task), (S.OUT_FOR_DELIVERY, S.OUT_FOR_DELIVERY, old))
        self.assertEqual(event.changes["holder"]["from"]["id"], self.shipper.pk)
        self.assertEqual(event.changes["holder"]["to"]["id"], self.other.pk)

    def test_locked_candidate_rolls_back_then_can_choose_another(self):
        old = self.prepare_task()
        self.ok(self.swap())
        lock_account(self.admin, self.other.pk)
        before = (self.fresh().updated_at, ShipmentEvent.objects.count(), Notification.objects.count())
        self.error(self.confirm(), code=ErrorCode.CONFLICT)
        old.refresh_from_db()
        self.assertEqual((old.status, old.swap_candidate_id), (T.PENDING_SWAP_HANDOVER, self.other.pk))
        self.assertEqual((self.fresh().updated_at, ShipmentEvent.objects.count(), Notification.objects.count()), before)
        self.assertFalse(Handover.objects.exists())
        self.assertEqual(Task.objects.count(), 1)
        self.ok(self.swap(self.third))
        self.ok(self.confirm())
        self.assertEqual(Task.objects.get(status=T.ACTIVE).shipper, self.third)

    def test_issue_is_append_only_keeps_pending_and_deduplicates(self):
        old = self.prepare_task()
        self.ok(self.swap())
        version = self.fresh().updated_at.isoformat()
        body = {"reason": "  Thiếu một kiện  "}
        self.ok(self.post_action("report-swap-issue", body, version))
        self.ok(self.post_action("report-swap-issue", body, version))
        old.refresh_from_db()
        self.assertEqual((old.status, old.swap_candidate_id), (T.PENDING_SWAP_HANDOVER, self.other.pk))
        self.assertEqual(ShipmentEvent.objects.filter(action=A.REPORT_SWAP_ISSUE).count(), 1)
        event = ShipmentEvent.objects.get(action=A.REPORT_SWAP_ISSUE)
        self.assertEqual((event.reason, event.task), ("Thiếu một kiện", old))
        self.assertNotEqual(self.fresh().updated_at.isoformat(), version)
        self.assertFalse(Handover.objects.exists())
        self.assertFalse(TaskResult.objects.exists())
        self.assertEqual(Notification.objects.count(), 1)

    def test_recall_allows_redelivery_by_someone_else_and_removes_locked_holder(self):
        Shipment.objects.filter(pk=self.shipment.pk).update(status=S.AWAITING_REDELIVERY, delivery_attempts=2,
                                                          holder_type=HolderType.SHIPPER, holder_shipper=self.shipper)
        lock_account(self.admin, self.shipper.pk)
        Notification.objects.all().delete()
        self.assertTrue(self.ok(self.detail())["holder_locked"])
        version = self.fresh().updated_at.isoformat()
        body = self.ok(self.post_action("recall-to-hub", {"discrepancy_note": "Đủ hàng"}, version))
        self.ok(self.post_action("recall-to-hub", version=version))
        self.assertEqual((body["status"], body["holder_type"], body["holder_shipper"], body["holder_locked"]),
                         (S.AWAITING_REDELIVERY, HolderType.HUB, None, False))
        self.assertFalse(Notification.objects.exists())
        h = Handover.objects.get()
        self.assertEqual((h.from_shipper, h.received_by, h.kind, h.task, h.discrepancy_note),
                         (self.shipper, self.admin, HandoverKind.REASSIGN_INTAKE, None, "Đủ hàng"))
        self.ok(self.post_action("assign-delivery", {"shipper_id": self.other.pk, "handed_over": True}))
        self.assertEqual(Task.objects.get().attempt_no, 3)
        self.assertEqual(self.fresh().delivery_attempts, 2)

    def test_recall_allows_return_intake_without_extra_trip(self):
        Shipment.objects.filter(pk=self.shipment.pk).update(status=S.AWAITING_RETURN, delivery_attempts=3,
                                                          holder_type=HolderType.SHIPPER, holder_shipper=self.shipper)
        self.ok(self.post_action("recall-to-hub"))
        self.ok(self.post_action("receive-return"))
        self.assertEqual((self.fresh().status, self.fresh().delivery_attempts), (S.AWAITING_SHOP_PICKUP, 3))
        self.assertFalse(Task.objects.exists())
        self.assertEqual(Handover.objects.count(), 2)

    def test_same_shipper_invalid_candidate_blank_reason_and_handover_required(self):
        self.prepare_task()
        error = self.error(self.swap(self.shipper), 400, ErrorCode.VALIDATION_ERROR)
        self.assertIn("shipper_id", error["fields"])
        for user in (self.shop, self.admin):
            self.error(self.swap(user), code=ErrorCode.CONFLICT)
        lock_account(self.admin, self.third.pk)
        self.error(self.swap(self.third), code=ErrorCode.CONFLICT)
        self.error(self.post_action("swap-shipper", {"shipper_id": 999999, "reason": "Đổi"}), code=ErrorCode.CONFLICT)
        for reason in ("", "   "):
            self.error(self.swap(reason=reason), 400, ErrorCode.VALIDATION_ERROR)
        self.error(self.post_action("swap-shipper", {"shipper_id": self.other.pk}), 400, ErrorCode.VALIDATION_ERROR)
        self.ok(self.swap())
        self.error(self.swap(self.shipper), 400, ErrorCode.VALIDATION_ERROR)
        for body in ({}, {"handed_over": False}):
            self.assertIn("handed_over", self.error(self.post_action("confirm-swap-handover", body),
                                                   400, ErrorCode.VALIDATION_ERROR)["fields"])
        self.error(self.post_action("report-swap-issue", {"reason": " "}), 400, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(Task.objects.count(), 1)
        self.assertFalse(Handover.objects.exists())

    def test_stale_versions_and_missing_versions_cannot_write(self):
        self.prepare_task()
        stale = self.fresh().updated_at.isoformat()
        Shipment.objects.filter(pk=self.shipment.pk).update(updated_at=timezone.now())
        self.error(self.swap(version=stale), code=ErrorCode.CONFLICT)
        self.ok(self.swap())
        stale = self.fresh().updated_at.isoformat()
        Shipment.objects.filter(pk=self.shipment.pk).update(updated_at=timezone.now())
        self.error(self.confirm(version=stale), code=ErrorCode.CONFLICT)
        self.error(self.post_action("report-swap-issue", {"reason": "Thiếu"}, stale), code=ErrorCode.CONFLICT)
        for name in ("swap-shipper", "confirm-swap-handover", "report-swap-issue", "recall-to-hub"):
            response = self.client.post(reverse("shipment-" + name, args=[self.shipment.pk]), {},
                                        content_type="application/json")
            self.error(response, 400, ErrorCode.VALIDATION_ERROR)
        self.assertFalse(Handover.objects.exists())

    def test_recall_stale_or_invalid_holder_or_open_task_rejected(self):
        Shipment.objects.filter(pk=self.shipment.pk).update(status=S.AWAITING_REDELIVERY)
        self.error(self.post_action("recall-to-hub"))  # vẫn ở Shop
        Shipment.objects.filter(pk=self.shipment.pk).update(holder_type=HolderType.SHIPPER, holder_shipper=self.shipper)
        stale = self.fresh().updated_at.isoformat()
        Shipment.objects.filter(pk=self.shipment.pk).update(updated_at=timezone.now())
        self.error(self.post_action("recall-to-hub", version=stale), code=ErrorCode.CONFLICT)
        # Dữ liệu bất thường vẫn bị chặn ở service, độc lập với trạng thái nguồn trong bảng.
        Task.objects.create(shipment=self.shipment, shipper=self.shipper, assigned_by=self.admin, type=TaskType.PICKUP)
        self.error(self.post_action("recall-to-hub"))
        self.assertFalse(Handover.objects.exists())

    def test_no_swap_for_return_failed_finished_or_missing_task(self):
        self.error(self.swap())
        task = self.prepare_task()
        Task.objects.filter(pk=task.pk).update(type=TaskType.RETURN, attempt_no=None)
        self.error(self.swap())  # giữ OUT_FOR_DELIVERY để kiểm guard loại nhiệm vụ thật sự
        Task.objects.filter(pk=task.pk).update(type=TaskType.DELIVERY, attempt_no=2, status=T.FAILED, closed_at=timezone.now())
        self.error(self.swap())
        for status in (S.DELIVERED, S.RETURNED_TO_SHOP, S.CANCELLED):
            Shipment.objects.filter(pk=self.shipment.pk).update(status=status)
            self.error(self.swap())
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_confirm_and_issue_require_pending_even_in_delivery_status(self):
        self.prepare_task()
        self.error(self.confirm())
        self.error(self.post_action("report-swap-issue", {"reason": "Thiếu"}))
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_transaction_rolls_back_if_notification_fails(self):
        task = self.prepare_task(TaskType.PICKUP)
        with patch("apps.dispatch.services.notify", side_effect=RuntimeError("test rollback")):
            with self.assertRaises(RuntimeError):
                services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", self.fresh().updated_at)
        task.refresh_from_db()
        self.assertEqual((task.status, task.replaced_by, Task.objects.count()), (T.ACTIVE, None, 1))
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_confirm_transaction_rolls_back_every_write(self):
        task = self.prepare_task()
        self.ok(self.swap())
        version = self.fresh().updated_at
        with patch("apps.dispatch.services.notify", side_effect=RuntimeError("test rollback")):
            with self.assertRaises(RuntimeError):
                services.confirm_swap_handover(self.admin, self.shipment.pk, "", version)
        task.refresh_from_db()
        self.assertEqual((task.status, task.swap_candidate, Task.objects.count()), (T.PENDING_SWAP_HANDOVER, self.other, 1))
        self.assertEqual((self.fresh().holder_shipper, self.fresh().updated_at), (self.shipper, version))
        self.assertFalse(Handover.objects.exists())
        self.assertFalse(ShipmentEvent.objects.filter(action=A.CONFIRM_SWAP_HANDOVER).exists())

    def test_open_tasks_includes_locked_pending_excludes_closed_and_other_shippers(self):
        task = self.prepare_task()
        self.ok(self.swap())
        lock_account(self.admin, self.shipper.pk)
        url = reverse("dispatch-shipper-open-tasks", args=[self.shipper.pk])
        body = self.ok(self.client.get(url))
        self.assertEqual(body, [{"id": task.pk, "type": TaskType.DELIVERY, "status": T.PENDING_SWAP_HANDOVER,
                                 "needs_attention": True, "shipment": {"id": self.shipment.pk,
                                 "tracking_code": None, "status": S.OUT_FOR_DELIVERY}}])
        self.assertEqual(self.ok(self.client.get(reverse("dispatch-shipper-open-tasks", args=[self.other.pk]))), [])
        self.ok(self.confirm())
        self.assertEqual(self.ok(self.client.get(url)), [])
        self.assertEqual(self.client.get(reverse("dispatch-shipper-open-tasks", args=[self.shop.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("dispatch-shipper-open-tasks", args=[999999])).status_code, 404)

    def test_permissions_and_not_found_precede_validation(self):
        self.prepare_task()
        names = ("swap-shipper", "confirm-swap-handover", "report-swap-issue", "recall-to-hub")
        for name in names:
            self.assertEqual(self.client.post(reverse("shipment-" + name, args=[999999]), {},
                                              content_type="application/json").status_code, 404)
        for user in (self.shop, self.shipper, self.other):
            self.client.force_login(user)
            for name in names:
                self.assertEqual(self.post_action(name).status_code, 403)
            self.assertEqual(self.client.get(reverse("dispatch-shipper-open-tasks", args=[self.shipper.pk])).status_code, 403)
        self.client.logout()
        for name in names:
            self.assertEqual(self.post_action(name).status_code, 401)
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_detail_has_no_n_plus_one_for_candidates_and_replacements(self):
        self.prepare_task()
        self.ok(self.swap())
        with CaptureQueriesContext(connection) as first:
            self.ok(self.detail())
        self.ok(self.confirm())
        self.ok(self.swap(self.third))
        with CaptureQueriesContext(connection) as second:
            self.ok(self.detail())
        self.assertEqual(len(first), len(second))
        self.client.force_login(self.shop)
        self.assertNotIn("tasks", self.ok(self.detail()))


@override_settings(HUB=HUB)
class SwapConcurrencyTests(RaceMixin, TransactionTestCase):
    def setUp(self):
        swap_fixture(self)
        Shipment.objects.filter(pk=self.shipment.pk).update(status=S.OUT_FOR_DELIVERY,
                                                          holder_type=HolderType.SHIPPER, holder_shipper=self.shipper)
        self.task = Task.objects.create(shipment=self.shipment, type=TaskType.DELIVERY, shipper=self.shipper,
                                       assigned_by=self.admin, attempt_no=1)

    def version(self):
        return Shipment.objects.get(pk=self.shipment.pk).updated_at

    def test_two_staff_confirm_create_only_one_replacement(self):
        services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", self.version())
        version = self.version()
        outcome = self.race(
            lambda: services.confirm_swap_handover(self.admin, self.shipment.pk, "", version),
            lambda: services.confirm_swap_handover(self.admin_2, self.shipment.pk, "", version),
        )
        self.assertEqual(outcome, ErrorCode.CONFLICT)
        self.assertEqual((Task.objects.count(), Handover.objects.count()), (2, 1))
        self.assertEqual(Task.objects.get(status=T.ACTIVE).shipper, self.other)
        self.assertEqual(Notification.objects.count(), 3)
        self.assertFalse(TaskResult.objects.exists())

    def test_candidate_locked_before_confirmation_is_rejected_without_writes(self):
        services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", self.version())
        version = self.version()
        outcome = self.race(
            lambda: lock_account(self.admin_2, self.other.pk),
            lambda: services.confirm_swap_handover(self.admin, self.shipment.pk, "", version),
        )
        self.assertEqual(outcome, ErrorCode.CONFLICT)
        self.assertEqual(Task.objects.count(), 1)
        self.assertFalse(Handover.objects.exists())

    def test_old_shipper_lock_and_confirmation_do_not_deadlock(self):
        services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", self.version())
        version = self.version()
        outcome = self.race(
            lambda: lock_account(self.admin_2, self.shipper.pk),
            lambda: services.confirm_swap_handover(self.admin, self.shipment.pk, "", version),
        )
        self.assertEqual(outcome, "ok")
        self.assertFalse(Task.objects.get(status=T.ACTIVE).needs_attention)
        self.assertEqual(Handover.objects.count(), 1)
