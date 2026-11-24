"""Spec 008 Phase 3: Shipper xem nhiệm vụ hoàn (UC04.8), báo đã đưa hàng hoàn về điểm tập kết (UC04.9 bước 1–3)."""
import re

from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import TaskStatus, TaskType
from apps.dispatch.models import Handover, Task
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward

A = ShipmentAction
LIST = reverse("task-list")
HUB = {"name": "Kho Cầu Giấy", "address": "12 Xuân Thủy", "phone": "0241234567"}
# D8: nhiệm vụ hoàn không cần thông tin người nhận / COD / liên hệ người gửi.
FORBIDDEN = {"receiver_name", "receiver_phone", "delivery_address", "cod_amount", "sender_phone", "pickup_address"}


def detail(pk, action=""):
    return reverse(f"task-{action}" if action else "task-detail", args=[pk])


def fresh(shipment):
    return Shipment.objects.get(pk=shipment.pk)


def returning(admin, shop, ward, shipper, code, reason="Khách từ chối nhận"):
    """Giao thất bại → NV quyết định hoàn (lý do) → phân công hoàn cho Shipper đang giữ hàng."""
    shipment = make_shipment(shop, ward)
    Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.DELIVERY_FAILED, tracking_code=code,
                                                   holder_type=HolderType.SHIPPER, holder_shipper=shipper,
                                                   delivery_attempts=1)
    services.decide_return(admin, shipment.pk, reason, fresh(shipment).updated_at)
    services.assign_return(admin, shipment.pk, shipper.pk, fresh(shipment).updated_at)
    return fresh(shipment), Task.objects.get(shipment=shipment, type=TaskType.RETURN)


@override_settings(HUB=HUB)
class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop = make_user("shop_a", "0900000001", full_name="Shop Hoa")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER, full_name="Shipper Long")
        self.other = make_user("sp_b", "0900000006", UserRole.SHIPPER)
        self.shipment, self.task = returning(self.admin, self.shop, self.ward, self.shipper, "HTT261122AAAAA")
        Notification.objects.all().delete()
        self.client.force_login(self.shipper)

    def report(self, task=None):
        return self.client.post(detail((task or self.task).pk, "report-return-handover"))

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)


class ViewReturnTaskTests(Base):
    def test_list_shows_only_own_return_tasks_without_receiver_or_cod(self):
        returning(self.admin, self.shop, self.ward, self.other, "HTT261122BBBBB")
        rows = self.client.get(LIST, {"type": TaskType.RETURN}).json()["results"]
        self.assertEqual([r["id"] for r in rows], [self.task.pk])  # UC04.8 bước 2
        row = rows[0]
        self.assertEqual((row["type"], row["attempt_no"], row["handover_reported_at"]), (TaskType.RETURN, None, None))
        self.assertEqual((row["shipment"]["tracking_code"], row["shipment"]["package_count"]), ("HTT261122AAAAA", 2))
        self.assertFalse(FORBIDDEN & set(row["shipment"]))

    def test_detail_has_reason_and_report_action(self):
        data = self.ok(self.client.get(detail(self.task.pk)))
        self.assertEqual(data["allowed_actions"], [A.REPORT_RETURN_HANDOVER])  # không có tiếp nhận (BR1)
        self.assertEqual(data["shipment"]["return_reason"], "Khách từ chối nhận")
        self.assertEqual(data["shipment"]["package_description"], "Áo thun")
        self.assertFalse(FORBIDDEN & set(data["shipment"]))

    def test_other_shipper_404_staff_403(self):
        _, others = returning(self.admin, self.shop, self.ward, self.other, "HTT261122BBBBB")
        self.assertEqual(self.client.get(detail(others.pk)).status_code, 404)  # E1
        self.assertEqual(self.report(others).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.report().status_code, 403)

    def test_list_no_n_plus_one(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(LIST, {"type": TaskType.RETURN})
            return len(ctx.captured_queries)

        baseline = count()
        for i in range(3):
            returning(self.admin, self.shop, self.ward, self.shipper, f"HTT261122X{i}XXX")
        self.assertEqual(count(), baseline)


class ReportHandoverTests(Base):
    def test_report_keeps_returning_and_notifies_staff(self):
        data = self.ok(self.report())
        self.assertTrue(data["handover_reported_at"])
        self.assertEqual((data["status"], data["allowed_actions"]), (TaskStatus.ACTIVE, []))  # A1: chờ NV
        self.assertEqual(fresh(self.shipment).status, ShipmentStatus.RETURNING)
        event = ShipmentEvent.objects.get(action=A.REPORT_RETURN_HANDOVER)
        self.assertEqual((event.actor, event.task_id, event.from_status, event.to_status),
                         (self.shipper, self.task.pk, ShipmentStatus.RETURNING, ShipmentStatus.RETURNING))
        recipients = set(Notification.objects.values_list("recipient__username", flat=True))
        self.assertEqual(recipients, {"nv_a", "nv_b"})  # D9: mọi NV, không báo Shop
        self.assertTrue(all(n.kind == NotificationKind.RETURN_HANDOVER_REPORTED for n in Notification.objects.all()))
        self.assertIn("Shipper Long", Notification.objects.first().title)

    def test_resend_does_not_duplicate(self):
        self.ok(self.report())
        self.ok(self.report())
        self.assertEqual(ShipmentEvent.objects.filter(action=A.REPORT_RETURN_HANDOVER).count(), 1)
        self.assertEqual(Notification.objects.count(), 2)

    def test_staff_sees_report_then_receives(self):
        self.ok(self.report())
        self.client.force_login(self.admin)
        staff = self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()
        self.assertTrue(staff["tasks"][0]["handover_reported_at"])
        services.receive_return(self.admin, self.shipment.pk, "", fresh(self.shipment).updated_at)
        self.client.force_login(self.shipper)
        self.ok(self.report())  # đã báo trước đó → vẫn trả hiện tại sau khi nhiệm vụ đóng
        self.assertEqual(self.client.get(detail(self.task.pk)).json()["status"], TaskStatus.SUCCEEDED)

    def test_cannot_report_after_staff_received_without_report(self):
        services.receive_return(self.admin, self.shipment.pk, "", fresh(self.shipment).updated_at)
        self.error(self.report(), 409, ErrorCode.INVALID_TRANSITION)
        self.assertFalse(ShipmentEvent.objects.filter(action=A.REPORT_RETURN_HANDOVER).exists())

    def test_replaced_task_cannot_report_while_shipment_still_returning(self):
        """Dữ liệu bất thường: nhiệm vụ hoàn đã đóng không được báo; spec 009 D3 không tạo nhánh đổi người hoàn."""
        from django.utils import timezone

        Task.objects.filter(pk=self.task.pk).update(status=TaskStatus.REPLACED, closed_at=timezone.now())
        Task.objects.create(shipment=self.shipment, type=TaskType.RETURN, shipper=self.other, assigned_by=self.admin)
        self.assertEqual(fresh(self.shipment).status, ShipmentStatus.RETURNING)
        self.error(self.report(), 409, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(self.client.get(detail(self.task.pk)).json()["allowed_actions"], [])

    def test_return_reason_is_the_return_decision_not_later_notes(self):
        services.report_return_issue(self.admin, self.shipment.pk, "Thiếu 1 kiện", fresh(self.shipment).updated_at)
        data = self.ok(self.client.get(detail(self.task.pk)))
        self.assertEqual(data["shipment"]["return_reason"], "Khách từ chối nhận")

    def test_report_refuses_non_return_task(self):
        other = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=other.pk).update(status=ShipmentStatus.AWAITING_PICKUP, tracking_code="HTT261122CCCCC")
        services.assign_pickup(self.admin, other.pk, self.shipper.pk, fresh(other).updated_at)
        pickup = Task.objects.get(shipment=other)
        self.error(self.report(pickup), 409, ErrorCode.INVALID_TRANSITION)
        self.assertIsNone(Task.objects.get(pk=pickup.pk).handover_reported_at)

    def test_locks_shipment_before_task(self):
        with CaptureQueriesContext(connection) as ctx:
            self.ok(self.report())
        tables = [re.search(r'FROM "(\w+)"', q["sql"]).group(1)
                  for q in ctx.captured_queries if "FOR UPDATE" in q["sql"]]
        # Báo bàn giao phải khóa người ghi trước task để không deadlock với khóa tài khoản (spec 009 nghiệm thu).
        self.assertEqual(tables, ["shipments_shipment", "accounts_user", "dispatch_task"])


@override_settings(HUB=HUB)
class ConcurrencyTests(RaceMixin, TransactionTestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.shipment, self.task = returning(self.admin, self.shop, make_ward(), self.shipper, "HTT261122AAAAA")

    def test_staff_receives_first_then_report_refused(self):
        version = fresh(self.shipment).updated_at
        outcome = self.race(lambda: services.receive_return(self.admin, self.shipment.pk, "", version),
                            lambda: services.report_return_handover(self.shipper, self.task.pk))
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)  # thấy nhiệm vụ đã đóng
        self.assertIsNone(Task.objects.get().handover_reported_at)
        self.assertEqual(Handover.objects.count(), 1)

    def test_report_first_then_staff_receives(self):
        version = fresh(self.shipment).updated_at
        outcome = self.race(lambda: services.report_return_handover(self.shipper, self.task.pk),
                            lambda: services.receive_return(self.admin, self.shipment.pk, "", version))
        self.assertEqual(outcome, "ok")  # báo bàn giao không tăng phiên bản đơn → NV vẫn tiếp nhận được (D5)
        task = Task.objects.get()
        self.assertEqual(task.status, TaskStatus.SUCCEEDED)
        self.assertIsNotNone(task.handover_reported_at)
