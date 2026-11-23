"""Spec 006 Phase 3: Shipper xem nhiệm vụ lấy (UC04.1), lấy được (UC04.2), lấy thất bại (UC04.3)."""
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import FAIL_NOTE_REQUIRED_MESSAGE, PickupFailReason, TaskStatus, TaskType
from apps.dispatch.models import Task, TaskResult
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.permissions import shipments_visible_to
from apps.shipments.tests.factories import make_shipment, make_user, make_ward

LIST = reverse("task-list")
# D3: nhiệm vụ LẤY không được lộ những trường này.
FORBIDDEN = {"receiver_name", "receiver_phone", "delivery_ward", "delivery_address", "cod_amount"}


def detail(pk, action=""):
    return reverse(f"task-{action}" if action else "task-detail", args=[pk])


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

    def assigned(self, shipper, code):
        shipment = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.AWAITING_PICKUP, tracking_code=code)
        services.assign_pickup(self.admin, shipment.pk, shipper.pk, Shipment.objects.get(pk=shipment.pk).updated_at)
        return Shipment.objects.get(pk=shipment.pk), Task.objects.get(shipment=shipment)

    def error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)
        return response.json()["error"]

    # KHÔNG đặt tên `fail`: unittest dùng self.fail() để báo lỗi trong assertEqual — trùng tên làm mọi
    # assert sai trong file này lặng lẽ không báo (lỗi đã gặp ở spec 006 Phase 3).
    def post_fail(self, reason_code=PickupFailReason.SHOP_ABSENT, note="", task=None):
        return self.client.post(detail((task or self.task).pk, "fail-pickup"), {"reason_code": reason_code, "note": note},
                                content_type="application/json")


class ViewTaskTests(Base):
    def test_list_only_own_tasks_without_receiver_or_cod(self):
        self.assigned(self.other, "HTT261122BBBBB")  # nhiệm vụ của Shipper khác
        response = self.client.get(LIST)
        self.assertEqual(response.status_code, 200)
        rows = response.json()["results"]
        self.assertEqual([r["id"] for r in rows], [self.task.pk])  # UC04.1 BR1
        shipment = rows[0]["shipment"]
        self.assertEqual((shipment["tracking_code"], shipment["shop_name"], shipment["pickup_address"]),
                         ("HTT261122AAAAA", "Shop Hoa", "12 Hàng Bạc"))
        self.assertFalse(FORBIDDEN & set(shipment))

    def test_detail_has_package_info_and_actions_from_table(self):
        data = self.client.get(detail(self.task.pk)).json()
        self.assertEqual(data["allowed_actions"], [ShipmentAction.CONFIRM_PICKUP, ShipmentAction.FAIL_PICKUP])
        self.assertEqual((data["shipment"]["package_description"], data["shipment"]["package_count"]), ("Áo thun", 2))
        self.assertFalse(FORBIDDEN & set(data["shipment"]))
        self.assertIsNone(data["result"])

    def test_other_shippers_task_is_404(self):
        _, others = self.assigned(self.other, "HTT261122BBBBB")
        self.error(self.client.get(detail(others.pk)), 404, ErrorCode.NOT_FOUND)
        self.error(self.client.post(detail(others.pk, "confirm-pickup")), 404, ErrorCode.NOT_FOUND)
        self.error(self.post_fail(task=others), 404, ErrorCode.NOT_FOUND)  # 404 trước lỗi dữ liệu
        self.assertEqual(Task.objects.get(pk=others.pk).status, TaskStatus.ACTIVE)

    def test_open_filter_and_empty(self):
        self.client.post(detail(self.task.pk, "confirm-pickup"))
        self.assertEqual(self.client.get(LIST, {"open": "true"}).json()["count"], 0)  # A1: danh sách trống
        self.assertEqual(self.client.get(LIST, {"open": "false"}).json()["count"], 1)
        self.assertEqual(self.client.get(LIST).json()["count"], 1)
        self.assertEqual(self.client.get(LIST, {"type": "DELIVERY"}).json()["count"], 0)
        self.assertEqual(self.client.get(LIST, {"type": "X"}).status_code, 400)

    def test_shipper_cannot_use_shipment_or_staff_apis(self):
        for method, url in [("get", reverse("shipment-list")), ("get", reverse("shipment-detail", args=[self.shipment.pk])),
                            ("get", reverse("dispatch-shippers")),
                            ("post", reverse("shipment-receive-at-hub", args=[self.shipment.pk]))]:
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 403)

    def test_staff_and_shop_cannot_use_task_apis(self):
        for user in [self.admin, self.shop]:
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(LIST).status_code, 403)
                self.assertEqual(self.client.post(detail(self.task.pk, "confirm-pickup")).status_code, 403)

    def test_list_constant_queries(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(LIST)
            return len(ctx.captured_queries)

        baseline = count()
        for i in range(4):
            self.assigned(self.shipper, f"HTT261122C{i}AAA")
        self.assertEqual(count(), baseline)

    def test_shipment_scope_for_shipper(self):
        self.assigned(self.other, "HTT261122BBBBB")
        self.assertEqual(list(shipments_visible_to(self.shipper).values_list("id", flat=True)), [self.shipment.pk])
        # subquery, không JOIN+DISTINCT → khóa dòng được (PostgreSQL cấm FOR UPDATE cùng DISTINCT).
        # Phải lấy dòng thật: .count() không sinh FOR UPDATE nên không kiểm được gì.
        self.assertEqual(len(list(shipments_visible_to(self.shipper).select_for_update())), 1)


class ConfirmPickupTests(Base):
    def test_confirm_moves_goods_to_shipper_and_notifies_shop(self):
        response = self.client.post(detail(self.task.pk, "confirm-pickup"))
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data["status"], data["allowed_actions"]), (TaskStatus.SUCCEEDED, []))
        self.assertEqual(data["result"]["outcome"], TaskStatus.SUCCEEDED)
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        self.assertEqual((shipment.status, shipment.holder_type, shipment.holder_shipper),
                         (ShipmentStatus.PICKED_UP, HolderType.SHIPPER, self.shipper))  # chưa phải AT_HUB (BR1)
        self.assertIsNotNone(Task.objects.get(pk=self.task.pk).closed_at)
        event = ShipmentEvent.objects.get(action=ShipmentAction.CONFIRM_PICKUP)
        self.assertEqual((event.actor, event.task_id), (self.shipper, self.task.pk))
        notice = Notification.objects.get()
        self.assertEqual((notice.recipient, notice.kind), (self.shop, NotificationKind.PICKED_UP))
        self.assertIn("Shipper Long", notice.body)

    def test_resend_is_idempotent(self):
        """UC04.2 BR2: bấm 2 lần / mạng chập chờn gửi lại → không ghi trùng."""
        self.client.post(detail(self.task.pk, "confirm-pickup"))
        self.assertEqual(self.client.post(detail(self.task.pk, "confirm-pickup")).status_code, 200)
        self.assertEqual(TaskResult.objects.count(), 1)
        self.assertEqual(ShipmentEvent.objects.filter(action=ShipmentAction.CONFIRM_PICKUP).count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_cannot_confirm_after_failing(self):
        self.post_fail()
        error = self.error(self.client.post(detail(self.task.pk, "confirm-pickup")), 409, ErrorCode.INVALID_TRANSITION)
        self.assertIn("đã kết thúc", error["message"])  # E1: không ghi thêm kết quả
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).status, ShipmentStatus.PICKUP_FAILED)

    def test_pickup_actions_refuse_non_pickup_task(self):
        """Spec 007 sẽ có nhiệm vụ GIAO: 'Đã lấy hàng' / 'Lấy thất bại' không được chạy trên loại khác."""
        other = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=other.pk).update(status=ShipmentStatus.PICKUP_ASSIGNED, tracking_code="HTT261122DDDDD")
        delivery = Task.objects.create(shipment=other, type=TaskType.DELIVERY, attempt_no=1, shipper=self.shipper,
                                       assigned_by=self.admin)
        self.error(self.client.post(detail(delivery.pk, "confirm-pickup")), 409, ErrorCode.INVALID_TRANSITION)
        self.error(self.post_fail(task=delivery), 409, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Task.objects.get(pk=delivery.pk).status, TaskStatus.ACTIVE)
        self.assertEqual(Shipment.objects.get(pk=other.pk).status, ShipmentStatus.PICKUP_ASSIGNED)

    def test_staff_can_receive_after_confirm(self):
        """Nối tiếp Phase 2: hàng Shipper đang giữ → Nhân viên nhận tại điểm tập kết."""
        self.client.post(detail(self.task.pk, "confirm-pickup"))
        shipment = services.receive_at_hub(self.admin, self.shipment.pk, "",
                                           Shipment.objects.get(pk=self.shipment.pk).updated_at)
        self.assertEqual((shipment.status, shipment.holder_type), (ShipmentStatus.AT_HUB, HolderType.HUB))
        self.assertEqual(shipment.handovers.get().from_shipper, self.shipper)


class FailPickupTests(Base):
    def test_fail_records_reason_keeps_goods_at_shop_notifies(self):
        response = self.post_fail(PickupFailReason.NOT_READY, "  Shop hẹn 3h chiều ")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["result"]["reason_code"], PickupFailReason.NOT_READY)
        result = TaskResult.objects.get()
        self.assertEqual((result.outcome, result.note), (TaskStatus.FAILED, "Shop hẹn 3h chiều"))
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        self.assertEqual((shipment.status, shipment.holder_type, shipment.holder_shipper),
                         (ShipmentStatus.PICKUP_FAILED, HolderType.SHOP, None))  # BR2: chưa nhận hàng
        event = ShipmentEvent.objects.get(action=ShipmentAction.FAIL_PICKUP)
        self.assertEqual(event.reason, "Hàng chưa sẵn sàng — Shop hẹn 3h chiều")
        recipients = sorted(n.recipient.username for n in Notification.objects.filter(kind=NotificationKind.PICKUP_FAILED))
        self.assertEqual(recipients, ["nv_a", "nv_b", "shop_a"])  # bước 7: Shop + mọi Nhân viên

    def test_reason_validation(self):
        error = self.error(self.post_fail(PickupFailReason.OTHER, "   "), 400, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(error["fields"]["note"], [FAIL_NOTE_REQUIRED_MESSAGE])
        self.error(self.post_fail("LAZY"), 400, ErrorCode.VALIDATION_ERROR)
        response = self.client.post(detail(self.task.pk, "fail-pickup"), {}, content_type="application/json")
        self.assertIn("reason_code", self.error(response, 400, ErrorCode.VALIDATION_ERROR)["fields"])
        self.assertEqual(self.post_fail(PickupFailReason.OTHER, "Cổng khóa").status_code, 200)

    def test_resend_and_then_staff_decides(self):
        self.post_fail()
        self.assertEqual(self.post_fail().status_code, 200)
        self.assertEqual(TaskResult.objects.count(), 1)
        self.error(self.client.post(detail(self.task.pk, "confirm-pickup")), 409, ErrorCode.INVALID_TRANSITION)
        # Chỉ Nhân viên quyết định (BR1) → lấy lại → phân công lại → Shipper có nhiệm vụ mới.
        services.retry_pickup(self.admin, self.shipment.pk, "Hẹn lại", Shipment.objects.get(pk=self.shipment.pk).updated_at)
        services.assign_pickup(self.admin, self.shipment.pk, self.shipper.pk,
                               Shipment.objects.get(pk=self.shipment.pk).updated_at)
        statuses = [r["status"] for r in self.client.get(LIST).json()["results"]]
        self.assertEqual(statuses, [TaskStatus.ACTIVE, TaskStatus.FAILED])  # mới trước, lần cũ còn
        # Đơn lại ở "Đã phân công lấy" nhưng nhiệm vụ CŨ đã đóng → không được hiện nút trên nhiệm vụ cũ.
        self.assertEqual(self.client.get(detail(self.task.pk)).json()["allowed_actions"], [])
        self.error(self.client.post(detail(self.task.pk, "confirm-pickup")), 409, ErrorCode.INVALID_TRANSITION)


class ConcurrencyTests(RaceMixin, TransactionTestCase):
    """Bấm 'Đã lấy hàng' và 'Lấy thất bại' gần như cùng lúc (2 thiết bị): đúng một kết quả."""

    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        shipment = make_shipment(self.shop, make_ward())
        Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.AWAITING_PICKUP, tracking_code="HTT261122AAAAA")
        services.assign_pickup(self.admin, shipment.pk, self.shipper.pk, Shipment.objects.get(pk=shipment.pk).updated_at)
        self.task = Task.objects.get()

    def test_confirm_vs_fail_one_wins(self):
        results = self.run_parallel(
            lambda: services.confirm_pickup(self.shipper, self.task.pk),
            lambda: services.fail_pickup(self.shipper, self.task.pk, PickupFailReason.SHOP_ABSENT, ""),
        )
        self.assertEqual(results, [ErrorCode.INVALID_TRANSITION, "ok"])
        self.assertEqual(TaskResult.objects.count(), 1)
        task = Task.objects.get()
        expected = {TaskStatus.SUCCEEDED: ShipmentStatus.PICKED_UP, TaskStatus.FAILED: ShipmentStatus.PICKUP_FAILED}
        self.assertEqual(Shipment.objects.get().status, expected[task.status])  # đơn khớp nhiệm vụ

    def test_double_confirm_one_result(self):
        results = self.run_parallel(*[lambda: services.confirm_pickup(self.shipper, self.task.pk)] * 3)
        self.assertEqual(results, ["ok", "ok", "ok"])  # người sau thấy đã xong → trả hiện tại
        self.assertEqual(TaskResult.objects.count(), 1)
        self.assertEqual(ShipmentEvent.objects.filter(action=ShipmentAction.CONFIRM_PICKUP).count(), 1)
