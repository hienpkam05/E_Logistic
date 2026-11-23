"""Spec 007 Phase 3: Shipper xem nhiệm vụ giao (UC04.4), giao thành công + COD (UC04.5, 04.7), giao thất bại (UC04.6)."""
import re

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import (
    FAIL_NOTE_REQUIRED_MESSAGE,
    MAX_DELIVERY_ATTEMPTS,
    DeliveryFailReason,
    PickupFailReason,
    TaskStatus,
    TaskType,
)
from apps.dispatch.models import Task, TaskResult
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import COD_MAX_VND, HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward

A = ShipmentAction
LIST = reverse("task-list")
COD = 350_000
# D3: nhiệm vụ GIAO không cần thông tin đi lấy.
FORBIDDEN = {"sender_name", "sender_phone", "pickup_ward", "pickup_address"}


def detail(pk, action=""):
    return reverse(f"task-{action}" if action else "task-detail", args=[pk])


def at_hub(shop, ward, code, cod=COD):
    shipment = make_shipment(shop, ward, cod_amount=cod)
    Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.AT_HUB, tracking_code=code,
                                                   holder_type=HolderType.HUB)
    return Shipment.objects.get(pk=shipment.pk)


def fresh(shipment):
    return Shipment.objects.get(pk=shipment.pk)


class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop = make_user("shop_a", "0900000001", full_name="Shop Hoa")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER, full_name="Shipper Long")
        self.other = make_user("sp_b", "0900000006", UserRole.SHIPPER)
        self.shipment, self.task = self.assigned(self.shipper, "HTT261122AAAAA")
        Notification.objects.all().delete()  # chỉ đếm thông báo của thao tác Shipper
        self.client.force_login(self.shipper)

    def assigned(self, shipper, code, cod=COD):
        shipment = at_hub(self.shop, self.ward, code, cod)
        services.assign_delivery(self.admin, shipment.pk, shipper.pk, shipment.updated_at)
        return fresh(shipment), Task.objects.get(shipment=shipment, status=TaskStatus.ACTIVE)

    def confirm(self, cod=COD, task=None):
        body = {} if cod is None else {"cod_collected": cod}
        return self.client.post(detail((task or self.task).pk, "confirm-delivery"), body,
                                content_type="application/json")

    def post_fail(self, reason_code=DeliveryFailReason.RECEIVER_UNREACHABLE, note="", task=None):
        return self.client.post(detail((task or self.task).pk, "fail-delivery"), {"reason_code": reason_code,
                                                                                  "note": note},
                                content_type="application/json")

    def error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)
        return response.json()["error"]

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def assert_nothing_recorded(self):
        """E1.1: không lưu kết quả thành công, không thu rời rạc, đơn vẫn Đang giao."""
        self.assertEqual(Task.objects.get(pk=self.task.pk).status, TaskStatus.ACTIVE)
        self.assertFalse(TaskResult.objects.filter(task=self.task).exists())
        shipment = fresh(self.shipment)
        self.assertEqual((shipment.status, shipment.delivery_attempts), (ShipmentStatus.OUT_FOR_DELIVERY, 0))
        self.assertFalse(ShipmentEvent.objects.filter(action=A.CONFIRM_DELIVERY).exists())
        self.assertFalse(Notification.objects.exists())

    def redeliver_to(self, shipper):
        """Sau thất bại: NV quyết định giao lại rồi phân công lần tiếp (người đang giữ — D7)."""
        services.decide_redelivery(self.admin, self.shipment.pk, "Hẹn lại", fresh(self.shipment).updated_at)
        services.assign_delivery(self.admin, self.shipment.pk, shipper.pk, fresh(self.shipment).updated_at)
        return Task.objects.get(shipment=self.shipment, status=TaskStatus.ACTIVE)


class ViewDeliveryTaskTests(Base):
    def test_list_shows_receiver_cod_attempt_not_pickup_info(self):
        self.assigned(self.other, "HTT261122BBBBB")
        rows = self.client.get(LIST).json()["results"]
        self.assertEqual([r["id"] for r in rows], [self.task.pk])  # UC04.4 BR1
        row = rows[0]
        self.assertEqual((row["type"], row["attempt_no"]), (TaskType.DELIVERY, 1))
        shipment = row["shipment"]
        self.assertEqual((shipment["receiver_name"], shipment["cod_amount"], shipment["shop_name"]),
                         ("Trần Thị B", COD, "Shop Hoa"))
        self.assertTrue(shipment["receiver_phone"])
        self.assertFalse(FORBIDDEN & set(shipment))

    def test_list_type_filter_defaults_to_all(self):
        """spec 006 mặc định chỉ PICKUP; spec 007 bỏ trống = mọi loại (D2)."""
        pickup_shipment = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=pickup_shipment.pk).update(status=ShipmentStatus.AWAITING_PICKUP,
                                                              tracking_code="HTT261122CCCCC")
        services.assign_pickup(self.admin, pickup_shipment.pk, self.shipper.pk, fresh(pickup_shipment).updated_at)
        types = lambda params: sorted(r["type"] for r in self.client.get(LIST, params).json()["results"])  # noqa: E731
        self.assertEqual(types({}), [TaskType.DELIVERY, TaskType.PICKUP])
        self.assertEqual(types({"type": TaskType.DELIVERY}), [TaskType.DELIVERY])
        self.assertEqual(types({"type": TaskType.PICKUP}), [TaskType.PICKUP])
        self.assertEqual(self.client.get(LIST, {"type": "X"}).status_code, 400)

    def test_detail_and_actions(self):
        data = self.ok(self.client.get(detail(self.task.pk)))
        self.assertEqual(data["allowed_actions"], [A.CONFIRM_DELIVERY, A.FAIL_DELIVERY])
        self.assertEqual((data["shipment"]["package_description"], data["shipment"]["delivery_address"]),
                         ("Áo thun", "5 Đội Cấn"))
        self.assertFalse(FORBIDDEN & set(data["shipment"]))

    def test_closed_task_hides_contact_phone_for_both_types(self):
        """D3 (UC04.4 BR2): SĐT chỉ dùng khi đang làm nhiệm vụ — áp dụng cả nhiệm vụ lấy (sửa so với spec 006)."""
        self.ok(self.confirm())
        data = self.ok(self.client.get(detail(self.task.pk)))
        self.assertIsNone(data["shipment"]["receiver_phone"])
        self.assertEqual(data["shipment"]["receiver_name"], "Trần Thị B")  # tên vẫn còn để đối chiếu
        self.assertIsNone(self.client.get(LIST).json()["results"][0]["shipment"]["receiver_phone"])

        pickup_shipment = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=pickup_shipment.pk).update(status=ShipmentStatus.AWAITING_PICKUP,
                                                              tracking_code="HTT261122CCCCC")
        services.assign_pickup(self.admin, pickup_shipment.pk, self.shipper.pk, fresh(pickup_shipment).updated_at)
        pickup = Task.objects.get(shipment=pickup_shipment)
        self.assertTrue(self.client.get(detail(pickup.pk)).json()["shipment"]["sender_phone"])  # đang mở: còn
        self.client.post(detail(pickup.pk, "confirm-pickup"))
        self.assertIsNone(self.client.get(detail(pickup.pk)).json()["shipment"]["sender_phone"])

    def test_other_shipper_404_and_staff_403(self):
        _, others = self.assigned(self.other, "HTT261122BBBBB")
        self.assertEqual(self.client.get(detail(others.pk)).status_code, 404)
        self.assertEqual(self.confirm(task=others).status_code, 404)
        self.assertEqual(self.post_fail(task=others).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.confirm().status_code, 403)

    def test_list_no_n_plus_one(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(LIST)
            return len(ctx.captured_queries)

        baseline = count()
        for i in range(3):
            self.assigned(self.shipper, f"HTT261122X{i}XXX")
        self.assertEqual(count(), baseline)


class ConfirmDeliveryTests(Base):
    def test_success_records_everything_together(self):
        data = self.ok(self.confirm())
        self.assertEqual((data["status"], data["allowed_actions"]), (TaskStatus.SUCCEEDED, []))
        self.assertEqual((data["result"]["cod_expected"], data["result"]["cod_collected"]), (COD, COD))  # bước 7
        shipment = fresh(self.shipment)
        self.assertEqual((shipment.status, shipment.holder_type, shipment.holder_shipper),
                         (ShipmentStatus.DELIVERED, HolderType.RECIPIENT, None))
        self.assertEqual(shipment.delivery_attempts, 1)
        result = TaskResult.objects.get(task=self.task)
        self.assertEqual((result.recorded_by, result.reason_code), (self.shipper, None))
        event = ShipmentEvent.objects.get(action=A.CONFIRM_DELIVERY)
        self.assertEqual((event.task_id, event.actor), (self.task.pk, self.shipper))
        self.assertEqual(event.changes["cod_collected"], {"from": None, "to": COD})
        self.assertEqual(event.changes["delivery_attempts"], {"from": 0, "to": 1})
        note = Notification.objects.get()
        self.assertEqual((note.kind, note.recipient), (NotificationKind.DELIVERED, self.shop))
        self.assertIn("350.000 ₫", note.body)

    def test_short_and_over_collection_rejected_with_difference(self):
        """UC04.7 E1.1: chỉ rõ chênh lệch; không ghi gì."""
        for cod, expected in ((330_000, "Thiếu 20.000 ₫ so với COD phải thu 350.000 ₫."),
                              (370_000, "Thừa 20.000 ₫ so với COD phải thu 350.000 ₫.")):
            with self.subTest(cod=cod):
                error = self.error(self.confirm(cod), 400, ErrorCode.VALIDATION_ERROR)
                self.assertEqual(error["fields"]["cod_collected"], [expected])
        self.assert_nothing_recorded()

    def test_invalid_amounts(self):
        """Bị từ chối ở bước kiểm dữ liệu, TRƯỚC khi so với phải thu — không ra câu "Thiếu 350.001 ₫" vô nghĩa."""
        for cod in (None, -1, COD_MAX_VND + 1, "abc", 1.5):
            with self.subTest(cod=cod):
                error = self.error(self.confirm(cod), 400, ErrorCode.VALIDATION_ERROR)
                message = " ".join(error["fields"]["cod_collected"])
                self.assertNotIn("so với COD phải thu", message)
        self.assert_nothing_recorded()

    def test_locks_shipment_before_task(self):
        """Quy ước spec 001 mục 3.6: khóa ĐƠN rồi mới NHIỆM VỤ (cùng thứ tự với thao tác Nhân viên) — tránh deadlock
        khi spec 009 đổi Shipper trên đơn đang giao."""
        _, second = self.assigned(self.shipper, "HTT261122BBBBB")  # phân công NGOÀI vùng đo
        for action in (lambda: self.confirm(), lambda: self.post_fail(task=second)):
            with CaptureQueriesContext(connection) as ctx:
                self.ok(action())
            tables = [re.search(r'FROM "(\w+)"', q["sql"]).group(1)
                      for q in ctx.captured_queries if "FOR UPDATE" in q["sql"]]
            self.assertEqual(tables, ["shipments_shipment", "dispatch_task"])

    def test_order_without_cod_records_zero(self):
        """A1: phải thu = thực thu = 0, không phát sinh khoản thu."""
        shipment, task = self.assigned(self.shipper, "HTT261122BBBBB", cod=0)
        Notification.objects.all().delete()
        self.error(self.confirm(1, task=task), 400, ErrorCode.VALIDATION_ERROR)
        data = self.ok(self.confirm(0, task=task))
        self.assertEqual((data["result"]["cod_expected"], data["result"]["cod_collected"]), (0, 0))
        self.assertEqual(Notification.objects.get().body, "")  # không nêu tiền

    def test_resend_does_not_add_money_or_attempts(self):
        """BR2: gửi lại (kể cả số khác) → trả kết quả đã có."""
        self.ok(self.confirm())
        data = self.ok(self.confirm(999))
        self.assertEqual(data["result"]["cod_collected"], COD)
        self.assertEqual(TaskResult.objects.count(), 1)
        self.assertEqual(fresh(self.shipment).delivery_attempts, 1)
        self.assertEqual(ShipmentEvent.objects.filter(action=A.CONFIRM_DELIVERY).count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_cannot_confirm_after_failing(self):
        self.ok(self.post_fail())
        self.error(self.confirm(), 409, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(fresh(self.shipment).status, ShipmentStatus.DELIVERY_FAILED)

    def test_attempt_number_follows_task(self):
        """Giao được ở lần 2: số lần = 2 (gán theo nhiệm vụ, không cộng)."""
        self.ok(self.post_fail())
        task = self.redeliver_to(self.shipper)
        self.assertEqual(fresh(self.shipment).delivery_attempts, 1)  # phân công không tăng
        self.ok(self.confirm(task=task))
        self.assertEqual(fresh(self.shipment).delivery_attempts, 2)

    def test_delivery_actions_refuse_pickup_task(self):
        pickup_shipment = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=pickup_shipment.pk).update(status=ShipmentStatus.AWAITING_PICKUP,
                                                              tracking_code="HTT261122CCCCC")
        services.assign_pickup(self.admin, pickup_shipment.pk, self.shipper.pk, fresh(pickup_shipment).updated_at)
        pickup = Task.objects.get(shipment=pickup_shipment)
        self.error(self.confirm(0, task=pickup), 409, ErrorCode.INVALID_TRANSITION)
        self.error(self.post_fail(task=pickup), 409, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Task.objects.get(pk=pickup.pk).status, TaskStatus.ACTIVE)


class FailDeliveryTests(Base):
    def test_failure_counts_attempt_keeps_goods_with_shipper(self):
        data = self.ok(self.post_fail(DeliveryFailReason.RECEIVER_REFUSED, " Khách đổi ý "))
        self.assertEqual(data["result"]["reason_code"], DeliveryFailReason.RECEIVER_REFUSED)
        self.assertIsNone(data["result"]["cod_collected"])
        shipment = fresh(self.shipment)
        self.assertEqual((shipment.status, shipment.delivery_attempts), (ShipmentStatus.DELIVERY_FAILED, 1))
        self.assertEqual((shipment.holder_type, shipment.holder_shipper), (HolderType.SHIPPER, self.shipper))
        event = ShipmentEvent.objects.get(action=A.FAIL_DELIVERY)
        self.assertEqual(event.reason, "Người nhận từ chối nhận — Khách đổi ý")
        self.assertEqual(event.changes["delivery_attempts"], {"from": 0, "to": 1})
        recipients = set(Notification.objects.values_list("recipient__username", flat=True))
        self.assertEqual(recipients, {"shop_a", "nv_a", "nv_b"})  # bước 7: Shop + Nhân viên
        self.assertTrue(all("1/3" in n.title for n in Notification.objects.all()))
        self.assertFalse(Task.objects.filter(shipment=self.shipment, status=TaskStatus.ACTIVE).exists())  # không tự tạo

    def test_reason_rules(self):
        error = self.error(self.post_fail(DeliveryFailReason.OTHER, "  "), 400, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(error["fields"]["note"], [FAIL_NOTE_REQUIRED_MESSAGE])
        self.error(self.post_fail(PickupFailReason.SHOP_ABSENT), 400, ErrorCode.VALIDATION_ERROR)  # nhóm lấy hàng
        self.error(self.post_fail(""), 400, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(Task.objects.get(pk=self.task.pk).status, TaskStatus.ACTIVE)
        self.ok(self.post_fail(DeliveryFailReason.OTHER, "Chó dữ"))

    def test_resend_does_not_double_count(self):
        """E1.2: không ghi thêm lần thất bại, không tăng bộ đếm trùng."""
        self.ok(self.post_fail())
        self.ok(self.post_fail(DeliveryFailReason.RECEIVER_REFUSED))
        self.assertEqual(fresh(self.shipment).delivery_attempts, 1)
        self.assertEqual(TaskResult.objects.get().reason_code, DeliveryFailReason.RECEIVER_UNREACHABLE)
        self.error(self.confirm(), 409, ErrorCode.INVALID_TRANSITION)

    def test_third_failure_leaves_only_return(self):
        """A1: lần 3 thất bại → Nhân viên chỉ còn hoàn (nối Phase 2)."""
        task = self.task
        for attempt in range(1, MAX_DELIVERY_ATTEMPTS + 1):
            self.ok(self.post_fail(task=task))
            self.assertEqual(fresh(self.shipment).delivery_attempts, attempt)
            if attempt < MAX_DELIVERY_ATTEMPTS:
                task = self.redeliver_to(self.shipper)
        self.client.force_login(self.admin)
        staff = self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()
        self.assertEqual(staff["allowed_actions"], [A.DECIDE_RETURN])
        self.assertEqual(sorted(t["attempt_no"] for t in staff["tasks"]), [1, 2, 3])


class ConcurrencyTests(RaceMixin, TransactionTestCase):
    """Hai thiết bị bấm gần như cùng lúc: đúng một kết quả, số lần +1 đúng một lần."""

    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        shipment = at_hub(self.shop, make_ward(), "HTT261122AAAAA")
        services.assign_delivery(self.admin, shipment.pk, self.shipper.pk, shipment.updated_at)
        self.task = Task.objects.get()

    def test_confirm_vs_fail_one_wins(self):
        results = self.run_parallel(
            lambda: services.confirm_delivery(self.shipper, self.task.pk, COD),
            lambda: services.fail_delivery(self.shipper, self.task.pk, DeliveryFailReason.RECEIVER_UNREACHABLE, ""),
        )
        self.assertEqual(results, [ErrorCode.INVALID_TRANSITION, "ok"])
        self.assertEqual(TaskResult.objects.count(), 1)
        task, shipment = Task.objects.get(), Shipment.objects.get()
        expected = {TaskStatus.SUCCEEDED: ShipmentStatus.DELIVERED, TaskStatus.FAILED: ShipmentStatus.DELIVERY_FAILED}
        self.assertEqual(shipment.status, expected[task.status])
        self.assertEqual(shipment.delivery_attempts, 1)

    def test_triple_confirm_one_result(self):
        results = self.run_parallel(*[lambda: services.confirm_delivery(self.shipper, self.task.pk, COD)] * 3)
        self.assertEqual(results, ["ok", "ok", "ok"])
        self.assertEqual(TaskResult.objects.count(), 1)
        self.assertEqual(Shipment.objects.get().delivery_attempts, 1)
        self.assertEqual(Notification.objects.filter(kind=NotificationKind.DELIVERED).count(), 1)
