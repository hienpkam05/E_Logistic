"""Spec 009 Phase 3: quyền nhiệm vụ cũ/mới, báo bàn giao và giao dịch đồng thời."""
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.accounts.services import lock_account
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import DeliveryFailReason, TaskStatus, TaskType
from apps.dispatch.models import Handover, Task, TaskResult
from apps.dispatch.tests.test_staff_swap import HUB, swap_fixture
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent

A, S, T = ShipmentAction, ShipmentStatus, TaskStatus


def delivery_fixture(obj):
    swap_fixture(obj)
    Shipment.objects.filter(pk=obj.shipment.pk).update(status=S.OUT_FOR_DELIVERY,
        holder_type=HolderType.SHIPPER, holder_shipper=obj.shipper, delivery_attempts=1)
    obj.task = Task.objects.create(shipment=obj.shipment, type=TaskType.DELIVERY, shipper=obj.shipper,
                                   assigned_by=obj.admin, attempt_no=2)


@override_settings(HUB=HUB)
class ShipperSwapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        delivery_fixture(cls)

    def setUp(self):
        self.client.force_login(self.shipper)

    def fresh(self):
        return Shipment.objects.get(pk=self.shipment.pk)

    def start_swap(self):
        services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", self.fresh().updated_at)

    def confirm_swap(self):
        services.confirm_swap_handover(self.admin, self.shipment.pk, "", self.fresh().updated_at)

    def report(self, pk=None):
        return self.client.post(reverse("task-report-swap-handover", args=[pk or self.task.pk]))

    def task_detail(self, pk=None):
        return self.client.get(reverse("task-detail", args=[pk or self.task.pk])).json()

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def error(self, response, status=409, code=ErrorCode.INVALID_TRANSITION):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)

    def test_report_records_once_notifies_only_active_staff_and_keeps_holder(self):
        self.start_swap()
        self.admin_2.is_active = False
        self.admin_2.save(update_fields=["is_active"])
        Notification.objects.all().delete()
        version = self.fresh().updated_at
        self.assertEqual(self.task_detail()["allowed_actions"], [A.REPORT_SWAP_HANDOVER])
        first = self.ok(self.report())
        second = self.ok(self.report())
        self.assertEqual(first["handover_reported_at"], second["handover_reported_at"])
        self.assertIsNotNone(first["handover_reported_at"])
        self.assertEqual((first["status"], first["allowed_actions"]), (T.PENDING_SWAP_HANDOVER, []))
        self.assertEqual((self.fresh().status, self.fresh().holder_shipper, self.fresh().updated_at,
                          self.fresh().delivery_attempts), (S.OUT_FOR_DELIVERY, self.shipper, version, 1))
        event = ShipmentEvent.objects.get(action=A.REPORT_SWAP_HANDOVER)
        self.assertEqual((event.actor, event.task_id, event.from_status, event.to_status),
                         (self.shipper, self.task.pk, S.OUT_FOR_DELIVERY, S.OUT_FOR_DELIVERY))
        note = Notification.objects.get()
        self.assertEqual((note.recipient, note.kind), (self.admin, NotificationKind.SWAP_HANDOVER_REPORTED))
        self.assertIn(self.shipper.full_name, note.title)
        self.assertEqual(note.payload, {"shipment_id": self.shipment.pk})
        self.assertFalse(Handover.objects.exists())
        self.assertFalse(TaskResult.objects.exists())
        self.assertEqual(Task.objects.count(), 1)

    def test_report_notifies_all_active_staff(self):
        self.start_swap()
        Notification.objects.all().delete()
        self.ok(self.report())
        self.assertCountEqual(Notification.objects.values_list("recipient_id", flat=True),
                              [self.admin.pk, self.admin_2.pk])

    def test_pending_old_shipper_cannot_deliver_fail_or_record_cod_directly(self):
        self.start_swap()
        for action, data in (("confirm-delivery", {"cod_collected": self.shipment.cod_amount}),
                             ("confirm-delivery", {"cod_collected": 0}),
                             ("fail-delivery", {"reason_code": DeliveryFailReason.OTHER, "note": "Không gặp"})):
            self.error(self.client.post(reverse("task-" + action, args=[self.task.pk]), data,
                                        content_type="application/json"))
        self.assertFalse(TaskResult.objects.exists())
        self.assertEqual(self.fresh().delivery_attempts, 1)
        self.assertEqual(self.task_detail()["allowed_actions"], [A.REPORT_SWAP_HANDOVER])

    def test_candidate_cannot_see_or_report_before_confirmation(self):
        self.start_swap()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("task-list")).json()["results"], [])
        self.error(self.client.get(reverse("task-detail", args=[self.task.pk])), 404, ErrorCode.NOT_FOUND)
        self.error(self.report(), 404, ErrorCode.NOT_FOUND)
        self.error(self.client.post(reverse("task-confirm-delivery", args=[self.task.pk]),
                                    {"cod_collected": self.shipment.cod_amount}, content_type="application/json"),
                   404, ErrorCode.NOT_FOUND)

    def test_confirmation_removes_old_contact_and_grants_new_same_attempt(self):
        self.start_swap()
        self.ok(self.report())
        self.confirm_swap()
        old = self.task_detail()
        self.assertEqual((old["status"], old["allowed_actions"], old["shipment"]["receiver_phone"]),
                         (T.REPLACED, [], None))
        self.assertEqual(self.client.get(reverse("task-list"), {"open": "true"}).json()["results"], [])
        self.assertEqual(self.client.get(reverse("task-list"), {"open": "false"}).json()["results"][0]["id"], self.task.pk)
        self.ok(self.report())  # gửi lại lần đã báo sau khi nhiệm vụ đóng
        self.assertEqual(ShipmentEvent.objects.filter(action=A.REPORT_SWAP_HANDOVER).count(), 1)
        new = Task.objects.get(status=T.ACTIVE)
        self.error(self.client.get(reverse("task-detail", args=[new.pk])), 404, ErrorCode.NOT_FOUND)
        self.error(self.client.post(reverse("task-confirm-delivery", args=[self.task.pk]),
                                    {"cod_collected": self.shipment.cod_amount}, content_type="application/json"))
        self.client.force_login(self.other)
        body = self.task_detail(new.pk)
        self.assertEqual((body["attempt_no"], body["shipment"]["receiver_phone"]), (2, self.shipment.receiver_phone))
        self.assertEqual(body["allowed_actions"], [A.CONFIRM_DELIVERY, A.FAIL_DELIVERY])
        self.ok(self.client.post(reverse("task-confirm-delivery", args=[new.pk]),
                                 {"cod_collected": self.shipment.cod_amount}, content_type="application/json"))
        self.assertEqual(self.fresh().delivery_attempts, 2)
        self.assertEqual(TaskResult.objects.get().cod_collected, self.shipment.cod_amount)

    def test_cannot_report_active_wrong_type_wrong_shipment_status_or_closed(self):
        self.error(self.report())  # ACTIVE không phải chờ bàn giao
        self.start_swap()
        Shipment.objects.filter(pk=self.shipment.pk).update(status=S.AWAITING_REDELIVERY)
        self.error(self.report())  # trạng thái đơn cũng phải hợp lệ
        Shipment.objects.filter(pk=self.shipment.pk).update(status=S.OUT_FOR_DELIVERY)
        Task.objects.filter(pk=self.task.pk).update(type=TaskType.RETURN, attempt_no=None)
        self.error(self.report())
        Task.objects.filter(pk=self.task.pk).update(type=TaskType.DELIVERY, attempt_no=2)
        self.confirm_swap()
        self.error(self.report())  # chưa từng báo, không được báo lần đầu sau khi đã thay
        self.assertFalse(ShipmentEvent.objects.filter(action=A.REPORT_SWAP_HANDOVER).exists())

    def test_roles_missing_task_and_locked_session(self):
        self.start_swap()
        self.error(self.report(999999), 404, ErrorCode.NOT_FOUND)
        for user in (self.shop, self.admin):
            self.client.force_login(user)
            self.error(self.report(), 403, ErrorCode.PERMISSION_DENIED)
        self.client.force_login(self.shipper)
        self.shipper.is_active = False
        self.shipper.save(update_fields=["is_active"])
        self.error(self.report(), 401, ErrorCode.NOT_AUTHENTICATED)
        self.client.logout()
        self.error(self.report(), 401, ErrorCode.NOT_AUTHENTICATED)
        self.assertFalse(ShipmentEvent.objects.filter(action=A.REPORT_SWAP_HANDOVER).exists())

    def test_failed_notification_rolls_back_timestamp_and_event(self):
        self.start_swap()
        with patch("apps.dispatch.services.notify", side_effect=RuntimeError("rollback")):
            with self.assertRaises(RuntimeError):
                services.report_swap_handover(self.shipper, self.task.pk)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.handover_reported_at)
        self.assertFalse(ShipmentEvent.objects.filter(action=A.REPORT_SWAP_HANDOVER).exists())


@override_settings(HUB=HUB)
class ShipperSwapConcurrencyTests(RaceMixin, TransactionTestCase):
    def setUp(self):
        delivery_fixture(self)

    def version(self):
        return Shipment.objects.get(pk=self.shipment.pk).updated_at

    def test_account_locked_first_rejects_report_even_if_request_was_authenticated(self):
        self.start_swap()
        result = self.race(
            lambda: lock_account(self.admin, self.shipper.pk),
            lambda: services.report_swap_handover(self.shipper, self.task.pk))
        self.assertEqual(result, ErrorCode.NOT_AUTHENTICATED)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.handover_reported_at)

    def test_report_then_account_lock_do_not_deadlock(self):
        self.start_swap()
        result = self.race(
            lambda: services.report_swap_handover(self.shipper, self.task.pk),
            lambda: lock_account(self.admin, self.shipper.pk))
        self.assertEqual(result, "ok")
        self.task.refresh_from_db()
        self.assertTrue(self.task.needs_attention)
        self.assertIsNotNone(self.task.handover_reported_at)

    def start_swap(self):
        services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", self.version())

    def test_swap_wins_then_old_delivery_cannot_write_cod(self):
        version = self.version()
        result = self.race(
            lambda: services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", version),
            lambda: services.confirm_delivery(self.shipper, self.task.pk, self.shipment.cod_amount))
        self.assertEqual(result, ErrorCode.INVALID_TRANSITION)
        self.assertFalse(TaskResult.objects.exists())
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).delivery_attempts, 1)

    def test_delivery_wins_then_staff_cannot_reopen_delivered_shipment(self):
        version = self.version()
        result = self.race(
            lambda: services.confirm_delivery(self.shipper, self.task.pk, self.shipment.cod_amount),
            lambda: services.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", version))
        self.assertEqual(result, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).status, S.DELIVERED)
        self.assertEqual(TaskResult.objects.get().cod_collected, self.shipment.cod_amount)
        self.assertEqual(Task.objects.count(), 1)

    def test_duplicate_reports_from_two_devices_create_one_event(self):
        self.start_swap()
        Notification.objects.all().delete()
        self.assertEqual(self.run_parallel(
            lambda: services.report_swap_handover(self.shipper, self.task.pk),
            lambda: services.report_swap_handover(self.shipper, self.task.pk)), ["ok", "ok"])
        self.assertEqual(ShipmentEvent.objects.filter(action=A.REPORT_SWAP_HANDOVER).count(), 1)
        self.assertEqual(Notification.objects.count(), 2)

    def test_report_first_does_not_invalidate_staff_confirmation(self):
        self.start_swap()
        version = self.version()
        result = self.race(
            lambda: services.report_swap_handover(self.shipper, self.task.pk),
            lambda: services.confirm_swap_handover(self.admin, self.shipment.pk, "", version))
        self.assertEqual(result, "ok")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, T.REPLACED)
        self.assertIsNotNone(self.task.handover_reported_at)
        self.assertEqual(Handover.objects.count(), 1)

    def test_confirmation_first_rejects_late_first_report(self):
        self.start_swap()
        version = self.version()
        result = self.race(
            lambda: services.confirm_swap_handover(self.admin, self.shipment.pk, "", version),
            lambda: services.report_swap_handover(self.shipper, self.task.pk))
        self.assertEqual(result, ErrorCode.INVALID_TRANSITION)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.handover_reported_at)
