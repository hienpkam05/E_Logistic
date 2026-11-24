"""Spec 004 Phase 3: sửa, hủy, lịch sử + tranh chấp đồng thời."""
import threading
import time

from django.db import connections, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.errors import BusinessError, ErrorCode
from apps.shipments import services
from apps.shipments.constants import ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent

from .factories import make_shipment, make_user, make_ward


def url(name, pk):
    return reverse(name, args=[pk])


class Base(TestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.shop_b = make_user("shop_b", "0900000002")
        self.ward = make_ward("00070", "Phường Hoàn Kiếm")
        self.ward2 = make_ward("00160", "Phường Ba Đình")
        self.shipment = make_shipment(self.shop, self.ward)
        self.client.force_login(self.shop)

    def version(self, pk=None):
        return self.client.get(url("shipment-detail", pk or self.shipment.pk)).json()["updated_at"]

    def patch(self, data, pk=None, client=None, updated_at=None):
        pk = pk or self.shipment.pk
        body = {**data, "updated_at": updated_at or self.version(pk)}
        return (client or self.client).patch(url("shipment-detail", pk), body, content_type="application/json")

    def cancel(self, pk=None, reason=None, client=None):
        body = {} if reason is None else {"reason": reason}
        return (client or self.client).post(url("shipment-cancel", pk or self.shipment.pk), body,
                                            content_type="application/json")

    def set_status(self, status):
        Shipment.objects.filter(pk=self.shipment.pk).update(status=status)

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        body = response.json()["error"]
        self.assertEqual(body["code"], code)
        return body


class UpdateTests(Base):
    def test_update_records_changes(self):
        response = self.patch({"receiver_phone": "0987654321", "delivery_ward": "00160", "cod_amount": 400000})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["status"], ShipmentStatus.PENDING_APPROVAL)
        self.assertEqual(body["delivery_ward"], {"code": "00160", "name": "Phường Ba Đình"})
        self.assertEqual(body["request_code"], self.shipment.request_code)  # giữ mã yêu cầu
        event = ShipmentEvent.objects.get(shipment=self.shipment)
        self.assertEqual((event.action, event.from_status, event.to_status, event.actor),
                         (ShipmentAction.UPDATE_REQUEST, "PENDING_APPROVAL", "PENDING_APPROVAL", self.shop))
        self.assertEqual(event.changes, {
            "receiver_phone": {"from": "0912345678", "to": "0987654321"},
            "delivery_ward": {"from": {"code": "00070", "name": "Phường Hoàn Kiếm"},
                              "to": {"code": "00160", "name": "Phường Ba Đình"}},
            "cod_amount": {"from": 350000, "to": 400000},
        })

    def test_no_change_no_event(self):
        self.assertEqual(self.patch({"receiver_phone": "0912345678"}).status_code, 200)
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_forbidden_fields_ignored(self):
        self.patch({"status": "DELIVERED", "shop": self.shop_b.pk, "tracking_code": "HTT1", "note": "Mới"})
        self.shipment.refresh_from_db()
        self.assertEqual((self.shipment.status, self.shipment.shop, self.shipment.tracking_code),
                         (ShipmentStatus.PENDING_APPROVAL, self.shop, None))
        self.assertEqual(self.shipment.note, "Mới")

    def test_invalid_data_saves_nothing(self):
        for data, field in (({"receiver_phone": "12"}, "receiver_phone"), ({"cod_amount": -1}, "cod_amount"),
                            ({"pickup_ward": "KHONG-CO"}, "pickup_ward"), ({"package_count": 0}, "package_count")):
            with self.subTest(field=field):
                err = self.assert_error(self.patch(data), 400, ErrorCode.VALIDATION_ERROR)
                self.assertIn(field, err["fields"])
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.receiver_phone, "0912345678")

    def test_missing_updated_at(self):
        response = self.client.patch(url("shipment-detail", self.shipment.pk), {"note": "x"},
                                     content_type="application/json")
        err = self.assert_error(response, 400, ErrorCode.VALIDATION_ERROR)
        self.assertIn("updated_at", err["fields"])

    def test_not_pending_rejected_with_clear_message(self):
        for status in (ShipmentStatus.AWAITING_PICKUP, ShipmentStatus.CANCELLED, ShipmentStatus.REJECTED):
            with self.subTest(status=status):
                version = self.version()
                self.set_status(status)
                err = self.assert_error(self.patch({"note": "x"}, updated_at=version), 409,
                                        ErrorCode.INVALID_TRANSITION)
                self.assertIn("không sửa được", err["message"])
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_stale_version_conflict(self):
        stale = self.version()
        self.assertEqual(self.patch({"note": "Lần 1"}).status_code, 200)
        err = self.assert_error(self.patch({"note": "Bản cũ"}, updated_at=stale), 409, ErrorCode.CONFLICT)
        self.assertIn("tải lại", err["message"])
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.note, "Lần 1")

    def test_other_shop_and_roles(self):
        other = make_shipment(self.shop_b, self.ward)
        self.assert_error(self.patch({"note": "x"}, pk=other.pk, updated_at="2026-01-01T00:00:00Z"), 404,
                          ErrorCode.NOT_FOUND)
        admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        client = Client()
        client.force_login(admin)
        response = client.patch(url("shipment-detail", self.shipment.pk), {"note": "x"},
                                content_type="application/json")
        self.assert_error(response, 403, ErrorCode.PERMISSION_DENIED)


class CancelTests(Base):
    def test_cancel_with_reason(self):
        response = self.cancel(reason="  Khách đổi ý ")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["status"], body["allowed_actions"]), (ShipmentStatus.CANCELLED, []))
        self.assertTrue(Shipment.objects.filter(pk=self.shipment.pk).exists())  # BR1: không xóa
        event = ShipmentEvent.objects.get()
        self.assertEqual((event.action, event.from_status, event.to_status, event.reason),
                         (ShipmentAction.CANCEL_REQUEST, "PENDING_APPROVAL", "CANCELLED", "Khách đổi ý"))

    def test_cancel_twice_is_idempotent(self):
        self.cancel()
        self.assertEqual(self.cancel().status_code, 200)
        self.assertEqual(ShipmentEvent.objects.count(), 1)

    def test_cannot_cancel_after_approval_or_rejection(self):
        for status in (ShipmentStatus.AWAITING_PICKUP, ShipmentStatus.REJECTED, ShipmentStatus.OUT_FOR_DELIVERY):
            with self.subTest(status=status):
                self.set_status(status)
                err = self.assert_error(self.cancel(), 409, ErrorCode.INVALID_TRANSITION)
                self.assertIn("không hủy được", err["message"])  # BR2: không hủy đơn đang vận chuyển
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_reason_limit_and_other_shop(self):
        err = self.assert_error(self.cancel(reason="x" * 501), 400, ErrorCode.VALIDATION_ERROR)
        self.assertIn("reason", err["fields"])
        other = make_shipment(self.shop_b, self.ward)
        self.assert_error(self.cancel(pk=other.pk), 404, ErrorCode.NOT_FOUND)
        other.refresh_from_db()
        self.assertEqual(other.status, ShipmentStatus.PENDING_APPROVAL)

    def test_cancelled_cannot_be_edited(self):
        version = self.version()
        self.cancel()
        self.assert_error(self.patch({"note": "x"}, updated_at=version), 409, ErrorCode.INVALID_TRANSITION)


class EventListTests(Base):
    def test_history_order_actor_changes(self):
        # Factory không ghi lịch sử tạo (service mới ghi) — thêm tay dòng tạo để kiểm thứ tự.
        ShipmentEvent.objects.create(shipment=self.shipment, action=ShipmentAction.CREATE_REQUEST,
                                     to_status=ShipmentStatus.PENDING_APPROVAL, actor=self.shop)
        self.patch({"cod_amount": 0})
        self.cancel(reason="Thôi gửi")
        body = self.client.get(url("shipment-events", self.shipment.pk)).json()
        self.assertEqual([e["action"] for e in body["results"]], ["CANCEL_REQUEST", "UPDATE_REQUEST", "CREATE_REQUEST"])
        first = body["results"][0]
        self.assertEqual(set(first), {"id", "action", "from_status", "to_status", "actor", "reason", "changes",
                                      "created_at", "task"})
        self.assertEqual(first["actor"], {"id": self.shop.pk, "full_name": self.shop.full_name})
        self.assertIsNone(first["task"])
        self.assertFalse(body["has_transport_activity"])
        self.assertEqual(body["results"][1]["changes"], {"cod_amount": {"from": 350000, "to": 0}})

    def test_other_shop_404_and_read_only(self):
        other = make_shipment(self.shop_b, self.ward)
        self.assert_error(self.client.get(url("shipment-events", other.pk)), 404, ErrorCode.NOT_FOUND)
        self.assert_error(self.client.post(url("shipment-events", self.shipment.pk)), 405, ErrorCode.REQUEST_ERROR)


class ConcurrencyTests(TransactionTestCase):
    """Shop sửa/hủy đúng lúc trạng thái đổi (mô phỏng Nhân viên duyệt — spec 005): không ghi đè."""

    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.shipment = make_shipment(self.shop, make_ward())

    def run_race(self, shop_action):
        locked = threading.Event()
        result = {}

        def approver():
            try:
                with transaction.atomic():
                    row = Shipment.objects.select_for_update().get(pk=self.shipment.pk)
                    locked.set()
                    time.sleep(0.5)  # giữ khóa: Shop phải đợi
                    row.status = ShipmentStatus.AWAITING_PICKUP
                    row.save(update_fields=["status", "updated_at"])
            finally:
                connections.close_all()

        def shop():
            locked.wait(timeout=10)
            try:
                shop_action()
                result["shop"] = "ok"
            except BusinessError as exc:
                result["shop"] = exc.code
            except Exception as exc:
                result["shop"] = repr(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=approver), threading.Thread(target=shop)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        return result["shop"]

    def test_update_waits_then_sees_new_status(self):
        version = Shipment.objects.get(pk=self.shipment.pk).updated_at
        outcome = self.run_race(lambda: services.update_request(self.shop, self.shipment.pk, {"note": "Sửa muộn"}, version))
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        self.assertEqual((shipment.status, shipment.note), (ShipmentStatus.AWAITING_PICKUP, ""))
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_cancel_waits_then_sees_new_status(self):
        outcome = self.run_race(lambda: services.cancel_request(self.shop, self.shipment.pk))
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).status, ShipmentStatus.AWAITING_PICKUP)
