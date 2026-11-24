"""Spec 008 Phase 2: Nhân viên phân công hoàn (UC06.7), tiếp nhận hàng hoàn (UC04.9), ghi sai lệch (E1),
xác nhận Shop nhận hàng hoàn (UC04.11)."""
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services
from apps.dispatch.constants import (
    REASON_REQUIRED_MESSAGE,
    RECEIVER_NAME_REQUIRED_MESSAGE,
    VERIFIED_REQUIRED_MESSAGE,
    HandoverKind,
    TaskStatus,
    TaskType,
)
from apps.dispatch.models import Handover, Task, TaskResult
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments.constants import HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward

A = ShipmentAction
HUB = {"name": "Kho Cầu Giấy", "address": "12 Xuân Thủy", "phone": "0241234567"}


def awaiting_return(shop, ward, code, holder):
    """Đơn Chờ xử lý hoàn (sau giao thất bại + quyết định hoàn — spec 007): hàng đang ở Shipper `holder`."""
    shipment = make_shipment(shop, ward)
    Shipment.objects.filter(pk=shipment.pk).update(status=ShipmentStatus.AWAITING_RETURN, tracking_code=code,
                                                   holder_type=HolderType.SHIPPER, holder_shipper=holder,
                                                   delivery_attempts=1)
    return Shipment.objects.get(pk=shipment.pk)


@override_settings(HUB=HUB)
class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop = make_user("shop_a", "0900000001", full_name="Shop Hoa")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN, full_name="Nhân viên A")
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER, full_name="Shipper Long")
        self.shipper_2 = make_user("sp_b", "0900000006", UserRole.SHIPPER, full_name="Shipper Bình")
        self.shipment = awaiting_return(self.shop, self.ward, "HTT261122AAAAA", self.shipper)
        self.client.force_login(self.admin)

    def fresh(self):
        return Shipment.objects.get(pk=self.shipment.pk)

    def post(self, name, body=None, version=None):
        data = {"updated_at": version or self.fresh().updated_at.isoformat(), **(body or {})}
        return self.client.post(reverse(f"shipment-{name}", args=[self.shipment.pk]), data,
                                content_type="application/json")

    def assign(self, shipper=None, **kw):
        return self.post("assign-return", {"shipper_id": (shipper or self.shipper).pk}, **kw)

    def receive(self, note="", **kw):
        return self.post("receive-return", {"discrepancy_note": note}, **kw)

    def confirm(self, name="Nguyễn Văn Hoa", verified=True, note="", **kw):
        body = {"note": note}
        if name is not None:
            body["receiver_name"] = name
        if verified is not None:
            body["verified"] = verified
        return self.post("confirm-shop-received", body, **kw)

    def detail(self):
        return self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)
        return response.json()["error"]

    def goods_at_hub(self):
        """Hàng đã nằm ở điểm tập kết khi Chờ xử lý hoàn (xảy ra sau đổi Shipper — spec 009)."""
        Shipment.objects.filter(pk=self.shipment.pk).update(holder_type=HolderType.HUB, holder_shipper=None)


class AssignReturnTests(Base):
    def test_assign_to_holder_creates_return_task(self):
        # D3: hàng ở Shipper → chưa tiếp nhận; spec 009 D6: nhận hàng về điểm tập kết (người giữ không đi hoàn được).
        self.assertEqual(self.detail()["allowed_actions"], [A.ASSIGN_RETURN, A.RECALL_TO_HUB])
        body = self.ok(self.assign())
        self.assertEqual(body["status"], ShipmentStatus.RETURNING)  # BR1: chưa phải Đã hoàn về Shop
        self.assertEqual((body["holder_type"], body["holder_shipper"]["id"]), (HolderType.SHIPPER, self.shipper.pk))
        task = Task.objects.get(shipment=self.shipment)
        self.assertEqual((task.type, task.status, task.attempt_no), (TaskType.RETURN, TaskStatus.ACTIVE, None))
        self.assertEqual(body["allowed_actions"], [A.RECEIVE_RETURN, A.REPORT_RETURN_ISSUE])
        event = ShipmentEvent.objects.get(action=A.ASSIGN_RETURN)
        self.assertEqual((event.task, event.from_status), (task, ShipmentStatus.AWAITING_RETURN))
        note = Notification.objects.get()
        self.assertEqual((note.kind, note.recipient), (NotificationKind.TASK_ASSIGNED, self.shipper))
        self.assertEqual(note.payload, {"shipment_id": self.shipment.pk, "task_id": task.pk})
        self.assertIn("Kho Cầu Giấy: 12 Xuân Thủy", note.body)  # D6: biết mang hàng về đâu

    def test_only_holder_resend_and_conflicts(self):
        error = self.error(self.assign(self.shipper_2), 409, ErrorCode.CONFLICT)  # A1.1 → spec 009
        self.assertIn("Shipper Long", error["message"])
        version = self.fresh().updated_at.isoformat()
        self.ok(self.assign(version=version))
        self.ok(self.assign(version=version))  # gửi lại
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_goods_at_hub_no_extra_trip(self):
        """A1.2 / A1.3: hàng đã ở điểm tập kết → không phân công được, nút là Tiếp nhận hàng hoàn."""
        self.goods_at_hub()
        self.assertEqual(self.detail()["allowed_actions"], [A.RECEIVE_RETURN])
        error = self.error(self.assign(), 409, ErrorCode.INVALID_TRANSITION)
        self.assertIn("Tiếp nhận hàng hoàn", error["message"])
        self.assertFalse(Task.objects.exists())

    def test_locked_holder_wrong_status_stale_and_permissions(self):
        stale = self.fresh().updated_at.isoformat()
        Shipment.objects.filter(pk=self.shipment.pk).update(updated_at=timezone.now())
        self.error(self.assign(version=stale), 409, ErrorCode.CONFLICT)
        self.shipper.is_active = False
        self.shipper.save(update_fields=["is_active"])
        self.error(self.assign(), 409, ErrorCode.CONFLICT)  # E1: người được chọn bị khóa
        Shipment.objects.filter(pk=self.shipment.pk).update(status=ShipmentStatus.DELIVERY_FAILED)
        self.error(self.assign(), 409, ErrorCode.INVALID_TRANSITION)  # E1: chưa có quyết định hoàn
        for user in (self.shop, self.shipper_2):
            self.client.force_login(user)
            self.assertEqual(self.assign().status_code, 403)
        self.assertFalse(Task.objects.exists())


class ReceiveReturnTests(Base):
    def test_receive_closes_task_and_moves_goods_to_hub(self):
        self.ok(self.assign())
        Notification.objects.all().delete()
        body = self.ok(self.receive("  Hộp móp nhẹ  "))
        self.assertEqual((body["status"], body["holder_type"], body["holder_shipper"]),
                         (ShipmentStatus.AWAITING_SHOP_PICKUP, HolderType.HUB, None))
        self.assertEqual(body["allowed_actions"], [A.CONFIRM_SHOP_RECEIVED])
        task = Task.objects.get()
        self.assertEqual(task.status, TaskStatus.SUCCEEDED)
        self.assertEqual(TaskResult.objects.get(task=task).recorded_by, self.admin)  # NV ghi kết quả (spec 001)
        handover = Handover.objects.get()
        self.assertEqual((handover.kind, handover.task, handover.from_shipper, handover.received_by),
                         (HandoverKind.RETURN_INTAKE, task, self.shipper, self.admin))
        self.assertEqual(handover.discrepancy_note, "Hộp móp nhẹ")
        event = ShipmentEvent.objects.get(action=A.RECEIVE_RETURN)
        self.assertEqual(event.changes["holder"]["to"], {"name": HolderType.HUB.label})
        note = Notification.objects.get()
        self.assertEqual((note.kind, note.recipient), (NotificationKind.RETURN_AT_HUB, self.shop))
        self.assertIn("Kho Cầu Giấy: 12 Xuân Thủy (SĐT 0241234567)", note.body)

    def test_works_without_shipper_report_and_resend(self):
        """D5: NV xác nhận được cả khi Shipper chưa báo bàn giao; gửi lại không ghi bàn giao thứ hai."""
        self.ok(self.assign())
        self.assertIsNone(self.detail()["tasks"][0]["handover_reported_at"])
        version = self.fresh().updated_at.isoformat()
        self.ok(self.receive(version=version))
        self.ok(self.receive(version=version))
        self.assertEqual(Handover.objects.count(), 1)
        self.client.force_login(self.admin_2)
        self.error(self.receive(), 409, ErrorCode.INVALID_TRANSITION)

    def test_receive_directly_when_goods_already_at_hub(self):
        """UC06.7 A1.2: tiếp nhận thẳng từ Chờ xử lý hoàn — không nhiệm vụ, không người giao."""
        self.goods_at_hub()
        self.assertEqual(self.ok(self.receive())["status"], ShipmentStatus.AWAITING_SHOP_PICKUP)
        handover = Handover.objects.get()
        self.assertEqual((handover.task, handover.from_shipper), (None, None))
        self.assertFalse(Task.objects.exists())

    def test_cannot_receive_while_goods_still_with_shipper_and_no_trip(self):
        error = self.error(self.receive(), 409, ErrorCode.INVALID_TRANSITION)
        self.assertIn("Shipper Long", error["message"])
        self.assertFalse(Handover.objects.exists())


class ReportIssueTests(Base):
    def test_issue_recorded_without_changing_state(self):
        self.ok(self.assign())
        for reason in ("", "  "):
            error = self.error(self.post("report-return-issue", {"reason": reason}), 400, ErrorCode.VALIDATION_ERROR)
            self.assertEqual(error["fields"]["reason"], [REASON_REQUIRED_MESSAGE])
        before = self.fresh().updated_at
        body = self.ok(self.post("report-return-issue", {"reason": "Thiếu 1 kiện"}))
        self.assertEqual(body["status"], ShipmentStatus.RETURNING)
        self.assertEqual(Task.objects.get().status, TaskStatus.ACTIVE)  # E1.2: nhiệm vụ vẫn mở
        self.assertGreater(self.fresh().updated_at, before)  # NV khác đang xem bản cũ phải tải lại
        event = ShipmentEvent.objects.get(action=A.REPORT_RETURN_ISSUE)
        self.assertEqual((event.reason, event.from_status, event.to_status, event.task_id),
                         ("Thiếu 1 kiện", ShipmentStatus.RETURNING, ShipmentStatus.RETURNING, Task.objects.get().pk))

    def test_resend_same_note_once_new_note_again(self):
        self.ok(self.assign())
        version = self.fresh().updated_at.isoformat()
        self.ok(self.post("report-return-issue", {"reason": "Thiếu 1 kiện"}, version=version))
        self.ok(self.post("report-return-issue", {"reason": "Thiếu 1 kiện"}, version=version))  # gửi lại
        self.ok(self.post("report-return-issue", {"reason": "Kiện ướt"}))
        self.assertEqual(ShipmentEvent.objects.filter(action=A.REPORT_RETURN_ISSUE).count(), 2)
        self.ok(self.receive("Thiếu 1 kiện, kiện ướt"))  # sau đó vẫn tiếp nhận được

    def test_only_while_returning(self):
        self.error(self.post("report-return-issue", {"reason": "x"}), 409, ErrorCode.INVALID_TRANSITION)


class ConfirmShopReceivedTests(Base):
    def setUp(self):
        super().setUp()
        self.goods_at_hub()
        self.ok(self.receive())
        Notification.objects.all().delete()

    def test_required_fields(self):
        for name in (None, "", "   "):
            with self.subTest(name=name):
                error = self.error(self.confirm(name=name), 400, ErrorCode.VALIDATION_ERROR)
                self.assertEqual(error["fields"]["receiver_name"], [RECEIVER_NAME_REQUIRED_MESSAGE])
        for verified in (None, False):
            with self.subTest(verified=verified):
                error = self.error(self.confirm(verified=verified), 400, ErrorCode.VALIDATION_ERROR)
                self.assertEqual(error["fields"]["verified"], [VERIFIED_REQUIRED_MESSAGE])
        self.assertEqual(self.fresh().status, ShipmentStatus.AWAITING_SHOP_PICKUP)  # A1: giữ nguyên

    def test_confirm_records_handover_and_finishes_return(self):
        body = self.ok(self.confirm("  Chị Hoa (chủ Shop)  ", note=" Đủ 2 kiện "))
        self.assertEqual((body["status"], body["holder_type"], body["allowed_actions"]),
                         (ShipmentStatus.RETURNED_TO_SHOP, HolderType.SHOP, []))
        self.assertEqual(body["return_result"]["receiver_name"], "Chị Hoa (chủ Shop)")
        handover = Handover.objects.get(kind=HandoverKind.SHOP_PICKUP)
        self.assertEqual((handover.receiver_name, handover.received_by, handover.discrepancy_note),
                         ("Chị Hoa (chủ Shop)", self.admin, "Đủ 2 kiện"))
        note = Notification.objects.get()
        self.assertEqual((note.kind, note.recipient), (NotificationKind.RETURN_COMPLETED, self.shop))
        self.assertIn("Chị Hoa (chủ Shop)", note.body)
        self.client.force_login(self.shop)
        shop_view = self.detail()
        self.assertEqual(shop_view["return_result"]["receiver_name"], "Chị Hoa (chủ Shop)")
        self.assertTrue(shop_view["return_result"]["received_at"])
        self.assertNotIn("tasks", shop_view)

    def test_resend_and_shop_cannot_confirm(self):
        version = self.fresh().updated_at.isoformat()
        self.ok(self.confirm(version=version))
        self.ok(self.confirm(version=version))  # E1: đã hoàn tất → không ghi thêm
        self.assertEqual(Handover.objects.filter(kind=HandoverKind.SHOP_PICKUP).count(), 1)
        self.client.force_login(self.shop)
        self.assertEqual(self.confirm().status_code, 403)  # BR1

    def test_return_result_only_when_returned(self):
        self.assertIsNone(self.detail()["return_result"])


class FullReturnFlowTests(Base):
    def test_checklist_scenario(self):
        """Checklist "Hoàn hàng" (phần NV): phân công hoàn → nhận → Chờ Shop đến lấy → Shop nhận → Đã hoàn về Shop."""
        self.ok(self.assign())
        Task.objects.filter(type=TaskType.RETURN).update(handover_reported_at=timezone.now())  # Shipper báo (Phase 3)
        self.assertTrue(self.detail()["tasks"][0]["handover_reported_at"])
        self.ok(self.receive())
        self.ok(self.confirm())
        actions = list(ShipmentEvent.objects.order_by("created_at", "id").values_list("action", flat=True))
        self.assertEqual(actions, [A.ASSIGN_RETURN, A.RECEIVE_RETURN, A.CONFIRM_SHOP_RECEIVED])
        self.assertEqual(self.fresh().status, ShipmentStatus.RETURNED_TO_SHOP)


@override_settings(HUB=HUB)
class ConcurrencyTests(RaceMixin, TransactionTestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.shipment = awaiting_return(self.shop, make_ward(), "HTT261122AAAAA", self.shipper)
        services.assign_return(self.admin, self.shipment.pk, self.shipper.pk, self.version())

    def version(self):
        return Shipment.objects.get(pk=self.shipment.pk).updated_at

    def test_two_staff_receive_one_handover(self):
        version = self.version()
        outcome = self.race(lambda: services.receive_return(self.admin, self.shipment.pk, "", version),
                            lambda: services.receive_return(self.admin_2, self.shipment.pk, "", version))
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Handover.objects.count(), 1)
        self.assertEqual(TaskResult.objects.count(), 1)

    def test_two_staff_confirm_shop_one_handover(self):
        services.receive_return(self.admin, self.shipment.pk, "", self.version())
        version = self.version()
        outcome = self.race(
            lambda: services.confirm_shop_received(self.admin, self.shipment.pk, "Chị Hoa", "", version),
            lambda: services.confirm_shop_received(self.admin_2, self.shipment.pk, "Chị Hoa", "", version),
        )
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Handover.objects.filter(kind=HandoverKind.SHOP_PICKUP).count(), 1)
