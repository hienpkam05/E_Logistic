"""Spec 006 Phase 2: Nhân viên phân công lấy (UC06.5), nhập điểm tập kết (UC04.10), xử lý lấy thất bại (UC04.13),
khóa Shipper còn nhiệm vụ mở (D9)."""
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.services import lock_account
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import REASON_REQUIRED_MESSAGE, HandoverKind, TaskStatus, TaskType
from apps.dispatch.models import Handover, Task
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward


def url(name, pk):
    return reverse(f"shipment-{name}", args=[pk])


def approved(shop, ward, code):
    """Đơn đã duyệt (Chờ lấy hàng) — trạng thái đầu vào của spec này."""
    shipment = make_shipment(shop, ward)
    Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.AWAITING_PICKUP, tracking_code=code)
    return Shipment.objects.get(pk=shipment.pk)


class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN, full_name="Nhân viên A")
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER, full_name="Shipper Long")
        self.shipper_2 = make_user("sp_b", "0900000006", UserRole.SHIPPER, full_name="Shipper Bình")
        self.shipment = approved(self.shop, self.ward, "HTT261122AAAAA")
        self.client.force_login(self.admin)

    def version(self, shipment=None):
        return Shipment.objects.get(pk=(shipment or self.shipment).pk).updated_at.isoformat()

    def post(self, name, body=None, shipment=None, version=None):
        shipment = shipment or self.shipment
        data = {"updated_at": version or self.version(shipment), **(body or {})}
        return self.client.post(url(name, shipment.pk), data, content_type="application/json")

    def assign(self, shipper=None, **kw):
        return self.post("assign-pickup", {"shipper_id": (shipper or self.shipper).pk}, **kw)

    def error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)
        return response.json()["error"]

    def to_picked_up(self, shipment=None):
        """Mô phỏng Shipper đã lấy hàng (service Shipper làm ở Phase 3)."""
        shipment = shipment or self.shipment
        services.assign_pickup(self.admin, shipment.pk, self.shipper.pk, Shipment.objects.get(pk=shipment.pk).updated_at)
        Task.objects.filter(shipment=shipment).update(status=TaskStatus.SUCCEEDED, closed_at=timezone.now())
        Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.PICKED_UP, holder_type=HolderType.SHIPPER,
                                                       holder_shipper=self.shipper)

    def to_pickup_failed(self):
        services.assign_pickup(self.admin, self.shipment.pk, self.shipper.pk, Shipment.objects.get(pk=self.shipment.pk).updated_at)
        Task.objects.filter(shipment=self.shipment).update(status=TaskStatus.FAILED, closed_at=timezone.now())
        Shipment.objects.filter(pk=self.shipment.pk).update(status=ShipmentStatus.PICKUP_FAILED)


class AssignPickupTests(Base):
    def test_assign_creates_task_history_notification(self):
        response = self.assign()
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["status"], ShipmentStatus.PICKUP_ASSIGNED)
        self.assertEqual(data["holder_type"], HolderType.SHOP)  # chưa lấy → hàng vẫn ở Shop
        self.assertEqual(len(data["tasks"]), 1)
        task_data = data["tasks"][0]
        self.assertEqual((task_data["type"], task_data["status"], task_data["shipper"]["id"]),
                         (TaskType.PICKUP, TaskStatus.ACTIVE, self.shipper.pk))

        task = Task.objects.get()
        self.assertEqual((task.assigned_by, task.shipper), (self.admin, self.shipper))
        event = ShipmentEvent.objects.get(shipment=self.shipment)
        self.assertEqual((event.action, event.task, event.actor), (ShipmentAction.ASSIGN_PICKUP, task, self.admin))
        self.assertEqual(event.changes, {"shipper": {"from": None, "to": {"id": self.shipper.pk, "name": "Shipper Long"}}})
        notice = Notification.objects.get()
        self.assertEqual((notice.recipient, notice.kind), (self.shipper, NotificationKind.TASK_ASSIGNED))
        self.assertIn("HTT261122AAAAA", notice.title)
        self.assertEqual(notice.payload, {"shipment_id": self.shipment.pk, "task_id": task.pk})

    def test_resend_same_shipper_is_idempotent_other_shipper_conflict(self):
        version = self.version()
        self.assertEqual(self.assign(version=version).status_code, 200)
        self.assertEqual(self.assign(version=version).status_code, 200)  # gửi lại, kể cả phiên bản cũ
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
        error = self.error(self.assign(self.shipper_2), 409, ErrorCode.CONFLICT)
        self.assertIn("Shipper Long", error["message"])  # BR2: đổi người dùng UC06.8, không phân công song song
        self.assertEqual(Task.objects.count(), 1)

    def test_shipper_must_be_active_shipper(self):
        locked = make_user("sp_lock", "0900000007", UserRole.SHIPPER, is_active=False)
        for bad in [locked, self.shop, self.admin_2]:
            with self.subTest(user=bad.username):
                self.error(self.assign(bad), 409, ErrorCode.CONFLICT)
        response = self.post("assign-pickup", {"shipper_id": 999999})
        self.error(response, 409, ErrorCode.CONFLICT)
        self.assertFalse(Task.objects.exists())
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).status, ShipmentStatus.AWAITING_PICKUP)

    def test_wrong_status_and_stale_version(self):
        pending = make_shipment(self.shop, self.ward)
        error = self.error(self.assign(shipment=pending), 409, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(error["message"], "Vận đơn đang ở trạng thái Chờ xác nhận nên không phân công lấy hàng được.")
        self.error(self.assign(version="2020-01-01T00:00:00Z"), 409, ErrorCode.CONFLICT)
        response = self.client.post(url("assign-pickup", self.shipment.pk), {"updated_at": self.version()},
                                    content_type="application/json")
        self.assertIn("shipper_id", self.error(response, 400, ErrorCode.VALIDATION_ERROR)["fields"])

    def test_only_staff(self):
        for user in [self.shop, self.shipper]:
            self.client.force_login(user)
            for name in ["assign-pickup", "receive-at-hub", "retry-pickup", "abandon-pickup"]:
                with self.subTest(user=user.username, name=name):
                    self.assertEqual(self.post(name, {"shipper_id": self.shipper.pk, "reason": "x"}).status_code, 403)
        self.assertFalse(Task.objects.exists())


class ShipperPickerTests(Base):
    def test_active_shippers_with_open_task_count_least_busy_first(self):
        make_user("sp_lock", "0900000007", UserRole.SHIPPER, is_active=False)
        # Người bận là "Shipper Bình" — đứng TRƯỚC theo tên, nên chỉ đúng khi xếp theo số việc trước.
        services.assign_pickup(self.admin, self.shipment.pk, self.shipper_2.pk, self.shipment.updated_at)
        response = self.client.get(reverse("dispatch-shippers"))
        self.assertEqual(response.status_code, 200)
        rows = [(r["username"], r["open_task_count"]) for r in response.json()]
        self.assertEqual(rows, [("sp_a", 0), ("sp_b", 1)])  # không có người bị khóa, Shop, Nhân viên
        self.assertEqual(response.json()[0]["phone"], "0900000004")

    def test_closed_tasks_not_counted_and_search(self):
        self.to_picked_up()
        rows = {r["username"]: r["open_task_count"] for r in self.client.get(reverse("dispatch-shippers")).json()}
        self.assertEqual(rows["sp_a"], 0)
        found = self.client.get(reverse("dispatch-shippers"), {"q": "bình"}).json()
        self.assertEqual([r["username"] for r in found], ["sp_b"])

    def test_single_query_regardless_of_shippers(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(reverse("dispatch-shippers"))
            return len(ctx.captured_queries)

        baseline = count()
        for i in range(5):
            make_user(f"sp_x{i}", f"09100000{i:02d}", UserRole.SHIPPER)
        self.assertEqual(count(), baseline)

    def test_only_staff(self):
        self.client.force_login(self.shipper)
        self.assertEqual(self.client.get(reverse("dispatch-shippers")).status_code, 403)


class DetailTests(Base):
    def test_staff_sees_tasks_shop_does_not(self):
        self.assign()
        staff = self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()
        self.assertEqual(len(staff["tasks"]), 1)
        self.assertIn("holder_shipper", staff)
        self.client.force_login(self.shop)
        shop = self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()
        self.assertNotIn("tasks", shop)  # quyền tối thiểu: Shop không thấy Shipper/nhiệm vụ nội bộ
        self.assertNotIn("holder_shipper", shop)

    def test_task_history_no_n_plus_one(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(reverse("shipment-detail", args=[self.shipment.pk]))
            return len(ctx.captured_queries)

        self.to_pickup_failed()
        baseline = count()
        for _ in range(3):  # lấy lại → phân công lại → thất bại ... nhiều nhiệm vụ đã đóng
            Shipment.objects.filter(pk=self.shipment.pk).update(status=ShipmentStatus.AWAITING_PICKUP)
            self.to_pickup_failed_again()
        self.assertEqual(Task.objects.filter(shipment=self.shipment).count(), 4)
        self.assertEqual(count(), baseline)

    def to_pickup_failed_again(self):
        services.assign_pickup(self.admin, self.shipment.pk, self.shipper_2.pk,
                               Shipment.objects.get(pk=self.shipment.pk).updated_at)
        Task.objects.filter(shipment=self.shipment, status=TaskStatus.ACTIVE).update(
            status=TaskStatus.FAILED, closed_at=timezone.now())
        Shipment.objects.filter(pk=self.shipment.pk).update(status=ShipmentStatus.PICKUP_FAILED)


class ReceiveAtHubTests(Base):
    def test_receive_records_handover_and_moves_goods_to_hub(self):
        self.to_picked_up()
        response = self.post("receive-at-hub", {"discrepancy_note": "  Thiếu 1 kiện  "})
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data["status"], data["holder_type"], data["holder_shipper"]),
                         (ShipmentStatus.AT_HUB, HolderType.HUB, None))
        handover = Handover.objects.get()
        self.assertEqual((handover.kind, handover.from_shipper, handover.received_by, handover.discrepancy_note),
                         (HandoverKind.HUB_INTAKE, self.shipper, self.admin, "Thiếu 1 kiện"))
        self.assertEqual(handover.task, Task.objects.get())
        event = ShipmentEvent.objects.filter(action=ShipmentAction.RECEIVE_AT_HUB).get()
        self.assertEqual(event.changes["holder"]["from"], {"id": self.shipper.pk, "name": "Shipper Long"})
        self.assertEqual(event.changes["discrepancy_note"]["to"], "Thiếu 1 kiện")

    def test_resend_same_staff_ok_other_staff_sees_status(self):
        self.to_picked_up()
        version = self.version()
        self.assertEqual(self.post("receive-at-hub", version=version).status_code, 200)
        self.assertEqual(self.post("receive-at-hub", version=version).status_code, 200)
        self.assertEqual(Handover.objects.count(), 1)  # E1.1 không tạo thêm xác nhận
        self.client.force_login(self.admin_2)
        error = self.error(self.post("receive-at-hub"), 409, ErrorCode.INVALID_TRANSITION)
        self.assertIn("Đã nhập điểm tập kết", error["message"])

    def test_not_before_pickup(self):
        self.assign()
        self.error(self.post("receive-at-hub"), 409, ErrorCode.INVALID_TRANSITION)  # BR1: chưa lấy được hàng
        self.assertFalse(Handover.objects.exists())


class PickupDecisionTests(Base):
    def test_retry_then_assign_again_keeps_history(self):
        self.to_pickup_failed()
        response = self.post("retry-pickup", {"reason": "  Shop hẹn chiều mai  "})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], ShipmentStatus.AWAITING_PICKUP)
        event = ShipmentEvent.objects.filter(action=ShipmentAction.RETRY_PICKUP).get()
        self.assertEqual(event.reason, "Shop hẹn chiều mai")
        notice = Notification.objects.get(kind=NotificationKind.PICKUP_RETRY)
        self.assertEqual((notice.recipient, notice.body), (self.shop, "Lý do: Shop hẹn chiều mai"))
        # UC06.5 BR1: phân công lại được, nhiệm vụ cũ (thất bại) còn nguyên.
        self.assertEqual(self.assign(self.shipper_2).status_code, 200)
        self.assertEqual(list(Task.objects.order_by("assigned_at").values_list("status", flat=True)),
                         [TaskStatus.FAILED, TaskStatus.ACTIVE])

    def test_abandon_ends_without_new_task(self):
        self.to_pickup_failed()
        response = self.post("abandon-pickup", {"reason": "Shop đóng cửa"})
        self.assertEqual(response.json()["status"], ShipmentStatus.PICKUP_ABANDONED)
        self.assertEqual(response.json()["tracking_code"], "HTT261122AAAAA")  # mã vận đơn giữ nguyên
        self.assertTrue(Notification.objects.filter(kind=NotificationKind.PICKUP_ABANDONED, recipient=self.shop).exists())
        self.error(self.assign(), 409, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Task.objects.count(), 1)

    def test_reason_required_and_resend(self):
        self.to_pickup_failed()
        for reason in ["", "   "]:
            error = self.error(self.post("retry-pickup", {"reason": reason}), 400, ErrorCode.VALIDATION_ERROR)
            self.assertEqual(error["fields"]["reason"], [REASON_REQUIRED_MESSAGE])
        version = self.version()
        self.post("abandon-pickup", {"reason": "x"}, version=version)
        self.assertEqual(self.post("abandon-pickup", {"reason": "x"}, version=version).status_code, 200)
        self.assertEqual(ShipmentEvent.objects.filter(action=ShipmentAction.ABANDON_PICKUP).count(), 1)
        self.error(self.post("retry-pickup", {"reason": "muộn"}), 409, ErrorCode.INVALID_TRANSITION)

    def test_only_from_pickup_failed(self):
        self.error(self.post("retry-pickup", {"reason": "x"}), 409, ErrorCode.INVALID_TRANSITION)
        self.error(self.post("abandon-pickup", {"reason": "x"}), 409, ErrorCode.INVALID_TRANSITION)


class LockedShipperTests(Base):
    def test_lock_flags_open_tasks_and_notifies_staff(self):
        services.assign_pickup(self.admin, self.shipment.pk, self.shipper.pk, self.shipment.updated_at)
        closed = approved(self.shop, self.ward, "HTT261122BBBBB")
        self.to_picked_up(closed)  # nhiệm vụ đã đóng của cùng Shipper — không bị đánh dấu
        lock_account(self.admin, self.shipper.pk, "Nghỉ việc")
        open_task = Task.objects.get(shipment=self.shipment)
        self.assertTrue(open_task.needs_attention)
        self.assertEqual(open_task.status, TaskStatus.ACTIVE)  # không tự đóng (đổi người ở spec 009)
        self.assertFalse(Task.objects.get(shipment=closed).needs_attention)
        notices = Notification.objects.filter(kind=NotificationKind.ACCOUNT_LOCKED_TASKS)
        self.assertEqual(sorted(n.recipient.username for n in notices), ["nv_a", "nv_b"])
        self.assertEqual(notices[0].payload, {"shipper_id": self.shipper.pk, "task_ids": [open_task.pk]})
        detail = self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()
        self.assertTrue(detail["tasks"][0]["needs_attention"])

    def test_lock_without_open_tasks_is_silent(self):
        lock_account(self.admin, self.shipper.pk)
        self.assertFalse(Notification.objects.exists())
        lock_account(self.admin, self.shop.pk)  # không phải Shipper
        self.assertFalse(Notification.objects.exists())


class ConcurrencyTests(RaceMixin, TransactionTestCase):
    """Hai thao tác thật song song: bên đầu giữ khóa 0.5s, bên sau phải đợi rồi thấy dữ liệu mới."""

    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.shipper_2 = make_user("sp_b", "0900000006", UserRole.SHIPPER)
        self.shipment = approved(self.shop, make_ward(), "HTT261122AAAAA")
        self.version = self.shipment.updated_at

    def assign(self, staff, shipper):
        return lambda: services.assign_pickup(staff, self.shipment.pk, shipper.pk, self.version)

    def test_two_staff_assign_different_shippers_one_task(self):
        outcome = self.race(self.assign(self.admin, self.shipper), self.assign(self.admin_2, self.shipper_2))
        self.assertEqual(outcome, ErrorCode.CONFLICT)
        self.assertEqual(list(Task.objects.values_list("shipper__username", flat=True)), ["sp_a"])
        self.assertEqual(Notification.objects.count(), 1)

    def test_lock_first_then_assign_refused(self):
        outcome = self.race(lambda: lock_account(self.admin, self.shipper.pk), self.assign(self.admin_2, self.shipper))
        self.assertEqual(outcome, ErrorCode.CONFLICT)
        self.assertFalse(Task.objects.exists())

    def test_assign_first_then_lock_flags_new_task(self):
        outcome = self.race(self.assign(self.admin, self.shipper), lambda: lock_account(self.admin_2, self.shipper.pk))
        self.assertEqual(outcome, "ok")
        self.assertTrue(Task.objects.get().needs_attention)  # khóa thấy nhiệm vụ vừa tạo, không bỏ sót
