"""Spec 007 Phase 2: Nhân viên phân công giao (UC06.6), quyết định giao lại / hoàn (UC04.12), giới hạn 3 lần (D8),
giao lại chỉ bằng Shipper đang giữ hàng (D7)."""
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import (
    HANDOVER_REQUIRED_MESSAGE,
    MAX_DELIVERY_ATTEMPTS,
    REASON_REQUIRED_MESSAGE,
    DeliveryFailReason,
    TaskStatus,
    TaskType,
)
from apps.dispatch.models import Task, TaskResult
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward

A = ShipmentAction


def url(name, pk):
    return reverse(f"shipment-{name}", args=[pk])


def at_hub(shop, ward, code):
    """Đơn Đã nhập điểm tập kết (đầu vào của spec này): hàng ở điểm tập kết."""
    shipment = make_shipment(shop, ward, cod_amount=350_000)
    Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.AT_HUB, tracking_code=code,
                                                   holder_type=HolderType.HUB)
    return Shipment.objects.get(pk=shipment.pk)


def shipper_fails(shipment):
    """Mô phỏng Shipper ghi giao thất bại (service Shipper làm ở Phase 3): nhiệm vụ đóng, số lần = lần của nhiệm vụ,
    hàng vẫn ở Shipper (UC04.6 bước 6–7)."""
    task = Task.objects.get(shipment=shipment, status=TaskStatus.ACTIVE)
    now = timezone.now()
    Task.objects.filter(pk=task.pk).update(status=TaskStatus.FAILED, closed_at=now)
    TaskResult.objects.create(task=task, outcome=TaskStatus.FAILED, reason_code=DeliveryFailReason.RECEIVER_UNREACHABLE,
                              recorded_by=task.shipper, recorded_at=now)
    Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.DELIVERY_FAILED,
                                                   delivery_attempts=task.attempt_no)
    return task


def shipper_delivers(shipment):
    task = Task.objects.get(shipment=shipment, status=TaskStatus.ACTIVE)
    now = timezone.now()
    Task.objects.filter(pk=task.pk).update(status=TaskStatus.SUCCEEDED, closed_at=now)
    TaskResult.objects.create(task=task, outcome=TaskStatus.SUCCEEDED, recorded_by=task.shipper, recorded_at=now,
                              cod_expected=shipment.cod_amount, cod_collected=shipment.cod_amount)
    Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.DELIVERED, holder_type=HolderType.RECIPIENT,
                                                   holder_shipper=None, delivery_attempts=task.attempt_no)


class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN, full_name="Nhân viên A")
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER, full_name="Shipper Long")
        self.shipper_2 = make_user("sp_b", "0900000006", UserRole.SHIPPER, full_name="Shipper Bình")
        self.shipment = at_hub(self.shop, self.ward, "HTT261122AAAAA")
        self.client.force_login(self.admin)

    def fresh(self):
        return Shipment.objects.get(pk=self.shipment.pk)

    def post(self, name, body=None, version=None):
        data = {"updated_at": version or self.fresh().updated_at.isoformat(), **(body or {})}
        return self.client.post(url(name, self.shipment.pk), data, content_type="application/json")

    def assign(self, shipper=None, handed_over=True, **kw):
        body = {"shipper_id": (shipper or self.shipper).pk}
        if handed_over is not None:
            body["handed_over"] = handed_over
        return self.post("assign-delivery", body, **kw)

    def decide(self, name, reason="Khách hẹn lại"):
        return self.post(name, {"reason": reason})

    def detail(self):
        return self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()

    def error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)
        return response.json()["error"]

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def fail_attempt(self, shipper=None):
        """Phân công (qua API) rồi Shipper thất bại."""
        self.ok(self.assign(shipper))
        return shipper_fails(self.shipment)

    def redeliver(self):
        self.ok(self.decide("decide-redelivery"))


class AssignDeliveryTests(Base):
    def test_first_assignment_from_hub(self):
        body = self.ok(self.assign())
        self.assertEqual(body["status"], ShipmentStatus.OUT_FOR_DELIVERY)
        self.assertEqual(body["delivery_attempts"], 0)  # UC06.6 điều kiện sau: không tăng số lần khi phân công
        self.assertEqual((body["holder_type"], body["holder_shipper"]["id"]), (HolderType.SHIPPER, self.shipper.pk))
        self.assertEqual((body["tasks"][0]["type"], body["tasks"][0]["attempt_no"]), (TaskType.DELIVERY, 1))
        self.assertEqual(body["allowed_actions"], [A.SWAP_SHIPPER])  # Đang giao: NV chờ Shipper; chỉ có đổi người (spec 009)

        task = Task.objects.get(shipment=self.shipment)
        self.assertEqual((task.status, task.shipper, task.assigned_by), (TaskStatus.ACTIVE, self.shipper, self.admin))
        event = ShipmentEvent.objects.get(shipment=self.shipment, action=A.ASSIGN_DELIVERY)
        self.assertEqual((event.task, event.actor, event.from_status), (task, self.admin, ShipmentStatus.AT_HUB))
        self.assertEqual(event.changes["attempt_no"], {"from": None, "to": 1})
        self.assertEqual(event.changes["holder"]["from"], {"name": HolderType.HUB.label})
        self.assertEqual(event.changes["holder"]["to"]["id"], self.shipper.pk)

        notes = {n.kind: n for n in Notification.objects.all()}
        self.assertEqual(set(notes), {NotificationKind.TASK_ASSIGNED, NotificationKind.OUT_FOR_DELIVERY})
        self.assertEqual(notes[NotificationKind.TASK_ASSIGNED].recipient, self.shipper)
        self.assertEqual(notes[NotificationKind.TASK_ASSIGNED].payload, {"shipment_id": self.shipment.pk,
                                                                         "task_id": task.pk})
        self.assertIn("1/3", notes[NotificationKind.TASK_ASSIGNED].body)
        self.assertEqual(notes[NotificationKind.OUT_FOR_DELIVERY].recipient, self.shop)
        self.assertIn("Shipper Long", notes[NotificationKind.OUT_FOR_DELIVERY].body)

    def test_handover_confirmation_required(self):
        """D6 (UC06.6 bước 3–4): chưa xác nhận Shipper đã nhận hàng → không phân công."""
        for handed_over in (None, False):
            with self.subTest(handed_over=handed_over):
                error = self.error(self.assign(handed_over=handed_over), 400, ErrorCode.VALIDATION_ERROR)
                self.assertEqual(error["fields"]["handed_over"], [HANDOVER_REQUIRED_MESSAGE])
        self.assertFalse(Task.objects.exists())

    def test_not_before_hub_intake(self):
        """BR1: lần đầu không bỏ qua UC04.10."""
        Shipment.objects.filter(pk=self.shipment.pk).update(status=ShipmentStatus.PICKED_UP)
        self.error(self.assign(), 409, ErrorCode.INVALID_TRANSITION)
        self.assertFalse(Task.objects.exists())

    def test_resend_same_shipper_ok_other_shipper_conflict(self):
        version = self.fresh().updated_at.isoformat()
        self.ok(self.assign(version=version))
        self.ok(self.assign(version=version))  # gửi lại bằng phiên bản cũ: trả hiện tại
        error = self.error(self.assign(self.shipper_2), 409, ErrorCode.CONFLICT)
        self.assertIn("Shipper Long", error["message"])
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 2)

    def test_shipper_must_be_active_shipper(self):
        self.shipper.is_active = False
        self.shipper.save(update_fields=["is_active"])
        self.error(self.assign(), 409, ErrorCode.CONFLICT)
        self.error(self.assign(self.admin_2), 409, ErrorCode.CONFLICT)
        self.assertFalse(Task.objects.exists())

    def test_stale_version(self):
        stale = self.fresh().updated_at.isoformat()
        Shipment.objects.filter(pk=self.shipment.pk).update(updated_at=timezone.now())
        self.error(self.assign(version=stale), 409, ErrorCode.CONFLICT)

    def test_only_staff(self):
        for user in (self.shop, self.shipper):
            self.client.force_login(user)
            self.assertEqual(self.assign().status_code, 403)


class RedeliveryAssignmentTests(Base):
    def setUp(self):
        super().setUp()
        self.fail_attempt()
        self.redeliver()

    def test_redeliver_with_holder_keeps_history(self):
        """UC06.6 A1: nhiệm vụ đợt mới cho người đang giữ hàng, lần 2; đợt cũ không bị sửa."""
        body = self.ok(self.assign())
        self.assertEqual(body["status"], ShipmentStatus.OUT_FOR_DELIVERY)
        self.assertEqual([t["attempt_no"] for t in body["tasks"]], [2, 1])
        self.assertEqual(body["tasks"][1]["status"], TaskStatus.FAILED)
        self.assertEqual(body["delivery_attempts"], 1)
        event = ShipmentEvent.objects.filter(action=A.ASSIGN_DELIVERY).latest("id")
        self.assertNotIn("holder", event.changes)  # người giữ không đổi
        self.assertEqual(event.from_status, ShipmentStatus.AWAITING_REDELIVERY)

    def test_other_shipper_refused_while_holder_has_goods(self):
        """D7 / UC06.6 A2: đổi người cần bàn giao về điểm tập kết (spec 009)."""
        error = self.error(self.assign(self.shipper_2), 409, ErrorCode.CONFLICT)
        self.assertIn("Shipper Long", error["message"])
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(self.fresh().status, ShipmentStatus.AWAITING_REDELIVERY)

    def test_locked_holder_flagged_and_blocks_assignment(self):
        self.shipper.is_active = False
        self.shipper.save(update_fields=["is_active"])
        self.assertTrue(self.detail()["holder_locked"])
        self.error(self.assign(), 409, ErrorCode.CONFLICT)  # người giữ đã khóa
        self.error(self.assign(self.shipper_2), 409, ErrorCode.CONFLICT)  # người khác: chờ đổi Shipper
        self.assertEqual(Task.objects.count(), 1)

    def test_limit_reached_is_checked_even_if_status_allows(self):
        """D8: phòng dữ liệu cũ — Chờ giao lại mà đã 3 lần vẫn bị chặn và không hiện nút."""
        Shipment.objects.filter(pk=self.shipment.pk).update(delivery_attempts=MAX_DELIVERY_ATTEMPTS)
        self.assertNotIn(A.ASSIGN_DELIVERY, self.detail()["allowed_actions"])
        self.error(self.assign(), 409, ErrorCode.LIMIT_REACHED)
        self.assertEqual(Task.objects.count(), 1)


class DecisionTests(Base):
    def test_actions_after_first_failure(self):
        self.fail_attempt()
        body = self.detail()
        self.assertEqual(body["allowed_actions"], [A.DECIDE_REDELIVERY, A.DECIDE_RETURN])
        self.assertEqual(body["holder_shipper"]["id"], self.shipper.pk)  # UC04.12 bước 2: người đang giữ
        self.assertEqual(body["tasks"][0]["result"]["reason_code"], DeliveryFailReason.RECEIVER_UNREACHABLE)
        self.assertFalse(body["holder_locked"])

    def test_redelivery(self):
        self.fail_attempt()
        Notification.objects.all().delete()
        body = self.ok(self.decide("decide-redelivery", "  Khách hẹn sau 17h  "))
        self.assertEqual(body["status"], ShipmentStatus.AWAITING_REDELIVERY)
        # Hàng còn ở Shipper cũ → thêm "Nhận hàng về điểm tập kết" để giao bằng người khác (spec 009 D6).
        self.assertEqual(body["allowed_actions"], [A.ASSIGN_DELIVERY, A.RECALL_TO_HUB])
        event = ShipmentEvent.objects.get(action=A.DECIDE_REDELIVERY)
        self.assertEqual((event.reason, event.actor), ("Khách hẹn sau 17h", self.admin))
        note = Notification.objects.get()
        self.assertEqual((note.kind, note.recipient), (NotificationKind.REDELIVERY_SCHEDULED, self.shop))
        self.assertIn("Khách hẹn sau 17h", note.body)

    def test_early_return(self):
        """A1.2: hoàn sớm ở lần đầu được (vd: khách từ chối nhận — UC04.6 BR2)."""
        self.fail_attempt()
        Notification.objects.all().delete()
        body = self.ok(self.decide("decide-return", "Khách từ chối nhận"))
        self.assertEqual(body["status"], ShipmentStatus.AWAITING_RETURN)  # nút tiếp theo: phân công hoàn (spec 008)
        self.assertNotIn(A.ASSIGN_DELIVERY, body["allowed_actions"])
        note = Notification.objects.get()
        self.assertEqual((note.kind, note.recipient), (NotificationKind.RETURN_DECIDED, self.shop))
        self.assertFalse(Task.objects.filter(type=TaskType.RETURN).exists())  # BR2: không tự tạo nhiệm vụ hoàn

    def test_three_attempts_then_only_return(self):
        """Toàn chu trình: 3 lần giao, mỗi lần phân công không tăng số lần; lần 3 thất bại → chỉ còn hoàn."""
        for attempt in range(1, MAX_DELIVERY_ATTEMPTS + 1):
            self.ok(self.assign())
            self.assertEqual(self.fresh().delivery_attempts, attempt - 1)
            shipper_fails(self.shipment)
            self.assertEqual(self.fresh().delivery_attempts, attempt)
            if attempt < MAX_DELIVERY_ATTEMPTS:
                self.redeliver()
        body = self.detail()
        self.assertEqual(body["allowed_actions"], [A.DECIDE_RETURN])  # UC04.6 A1
        self.assertEqual(sorted(t["attempt_no"] for t in body["tasks"]), [1, 2, 3])

        notifications = Notification.objects.count()
        error = self.error(self.decide("decide-redelivery"), 409, ErrorCode.LIMIT_REACHED)  # UC04.12 E1
        self.assertIn("3/3", error["message"])
        self.assertEqual(self.fresh().status, ShipmentStatus.DELIVERY_FAILED)
        self.assertEqual(Notification.objects.count(), notifications)
        self.assertEqual(ShipmentEvent.objects.filter(action=A.DECIDE_REDELIVERY).count(), MAX_DELIVERY_ATTEMPTS - 1)
        self.assertEqual(self.ok(self.decide("decide-return"))["status"], ShipmentStatus.AWAITING_RETURN)

    def test_reason_required_and_resend(self):
        self.fail_attempt()
        for name in ("decide-redelivery", "decide-return"):
            for reason in ("", "   "):
                error = self.error(self.decide(name, reason), 400, ErrorCode.VALIDATION_ERROR)
                self.assertEqual(error["fields"]["reason"], [REASON_REQUIRED_MESSAGE])
        version = self.fresh().updated_at.isoformat()
        self.ok(self.post("decide-redelivery", {"reason": "Hẹn lại"}, version=version))
        self.ok(self.post("decide-redelivery", {"reason": "Hẹn lại"}, version=version))  # gửi lại
        self.assertEqual(ShipmentEvent.objects.filter(action=A.DECIDE_REDELIVERY).count(), 1)
        self.client.force_login(self.admin_2)  # người khác: thấy trạng thái mới, không ghi đè
        self.error(self.decide("decide-return"), 409, ErrorCode.INVALID_TRANSITION)

    def test_only_from_delivery_failed(self):
        self.error(self.decide("decide-redelivery"), 409, ErrorCode.INVALID_TRANSITION)
        self.error(self.decide("decide-return"), 409, ErrorCode.INVALID_TRANSITION)

    def test_only_staff(self):
        self.fail_attempt()
        for user in (self.shop, self.shipper):
            self.client.force_login(user)
            for name in ("decide-redelivery", "decide-return"):
                self.assertEqual(self.decide(name).status_code, 403)


class DetailTests(Base):
    def test_shop_sees_delivery_result_not_internal_fields(self):
        self.client.force_login(self.shop)
        body = self.detail()
        self.assertIsNone(body["delivery"])
        self.assertNotIn("holder_locked", body)
        self.client.force_login(self.admin)
        self.ok(self.assign())
        shipper_delivers(self.shipment)
        self.client.force_login(self.shop)
        body = self.detail()
        self.assertEqual(body["status"], ShipmentStatus.DELIVERED)
        self.assertEqual((body["delivery"]["cod_collected"], body["delivery"]["attempt_no"]), (350_000, 1))
        self.assertTrue(body["delivery"]["delivered_at"])
        self.assertNotIn("tasks", body)

    def test_delivery_result_is_the_successful_attempt(self):
        """Thất bại lần 1, giao được lần 2 → Shop thấy lần 2 (không lấy nhầm kết quả thất bại cũ)."""
        self.fail_attempt()
        self.redeliver()
        self.ok(self.assign())
        shipper_delivers(self.shipment)
        self.client.force_login(self.shop)
        delivery = self.detail()["delivery"]
        self.assertEqual((delivery["attempt_no"], delivery["cod_collected"]), (2, 350_000))

    def test_staff_sees_cod_on_task_result(self):
        self.ok(self.assign())
        shipper_delivers(self.shipment)
        result = self.detail()["tasks"][0]["result"]
        self.assertEqual((result["cod_expected"], result["cod_collected"]), (350_000, 350_000))

    def test_no_n_plus_one_over_attempts(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.detail()
            return len(ctx.captured_queries)

        self.fail_attempt()
        baseline = count()
        self.redeliver()
        self.fail_attempt()
        self.redeliver()
        self.fail_attempt()
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(count(), baseline)


class ConcurrencyTests(RaceMixin, TransactionTestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.shipper_2 = make_user("sp_b", "0900000006", UserRole.SHIPPER)
        self.shipment = at_hub(self.shop, make_ward(), "HTT261122AAAAA")

    def version(self):
        return Shipment.objects.get(pk=self.shipment.pk).updated_at

    def test_two_staff_assign_delivery_one_task(self):
        version = self.version()
        outcome = self.race(
            lambda: services.assign_delivery(self.admin, self.shipment.pk, self.shipper.pk, version),
            lambda: services.assign_delivery(self.admin_2, self.shipment.pk, self.shipper_2.pk, version),
        )
        self.assertEqual(outcome, ErrorCode.CONFLICT)
        self.assertEqual(list(Task.objects.values_list("shipper__username", "attempt_no")), [("sp_a", 1)])
        self.assertEqual(Notification.objects.count(), 2)  # Shipper + Shop của lần thắng

    def test_redelivery_vs_return_one_decision(self):
        services.assign_delivery(self.admin, self.shipment.pk, self.shipper.pk, self.version())
        shipper_fails(self.shipment)
        version = self.version()
        outcome = self.race(
            lambda: services.decide_redelivery(self.admin, self.shipment.pk, "Hẹn lại", version),
            lambda: services.decide_return(self.admin_2, self.shipment.pk, "Hoàn", version),
        )
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)  # thấy Chờ giao lại → không hoàn đè
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).status, ShipmentStatus.AWAITING_REDELIVERY)
        self.assertFalse(ShipmentEvent.objects.filter(action=A.DECIDE_RETURN).exists())
