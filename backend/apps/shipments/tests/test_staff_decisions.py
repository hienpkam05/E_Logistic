"""Spec 005 Phase 3: Nhân viên duyệt (UC05.6) / từ chối (UC05.8) yêu cầu gửi hàng."""
import re
import threading
from unittest import mock

from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.shipments import services
from apps.shipments.constants import (
    EVENT_REASON_MAX_LENGTH,
    MISSING_VERSION_MESSAGE,
    REJECT_REASON_REQUIRED_MESSAGE,
    STALE_FOR_DECISION_MESSAGE,
    TRACKING_CODE_MAX_ATTEMPTS,
    TRACKING_CODE_REGEX,
    ShipmentAction,
    ShipmentStatus,
)
from apps.shipments.models import Shipment, ShipmentEvent

from .factories import make_shipment, make_user, make_ward


def approve_url(pk):
    return reverse("shipment-approve", args=[pk])


def reject_url(pk):
    return reverse("shipment-reject", args=[pk])


class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipper = make_user("shipper_a", "0900000004", UserRole.SHIPPER)
        self.shipment = make_shipment(self.shop, self.ward)
        self.client.force_login(self.admin)

    def version(self, shipment=None):
        return Shipment.objects.get(pk=(shipment or self.shipment).pk).updated_at.isoformat()

    def approve(self, version=None, shipment=None):
        shipment = shipment or self.shipment
        body = {"updated_at": version or self.version(shipment)}
        return self.client.post(approve_url(shipment.pk), body, content_type="application/json")

    def reject(self, reason="Địa chỉ giao không rõ số nhà", version=None):
        body = {"reason": reason, "updated_at": version or self.version()}
        return self.client.post(reject_url(self.shipment.pk), body, content_type="application/json")

    def assert_untouched(self):
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        self.assertEqual(shipment.status, ShipmentStatus.PENDING_APPROVAL)
        self.assertIsNone(shipment.tracking_code)
        self.assertFalse(ShipmentEvent.objects.filter(shipment=shipment).exists())
        self.assertFalse(Notification.objects.exists())


class ApproveTests(Base):
    def test_approve_creates_tracking_code_history_and_one_notification(self):
        response = self.approve()
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["status"], ShipmentStatus.AWAITING_PICKUP)
        self.assertRegex(data["tracking_code"], TRACKING_CODE_REGEX)
        self.assertEqual(data["request_code"], self.shipment.request_code)  # BR3: mã yêu cầu giữ nguyên
        self.assertNotIn(ShipmentAction.APPROVE_REQUEST, data["allowed_actions"])

        event = ShipmentEvent.objects.get(shipment=self.shipment)
        self.assertEqual((event.action, event.from_status, event.to_status, event.actor),
                         (ShipmentAction.APPROVE_REQUEST, ShipmentStatus.PENDING_APPROVAL,
                          ShipmentStatus.AWAITING_PICKUP, self.admin))
        self.assertEqual(event.changes, {"tracking_code": {"from": None, "to": data["tracking_code"]}})

        notice = Notification.objects.get()
        self.assertEqual((notice.recipient, notice.kind), (self.shop, NotificationKind.REQUEST_APPROVED))
        self.assertIn(self.shipment.request_code, notice.title)
        self.assertIn(data["tracking_code"], notice.body)
        self.assertEqual(notice.payload, {"shipment_id": self.shipment.pk})

        shipment = Shipment.objects.get(pk=self.shipment.pk)
        self.assertEqual(shipment.holder_type, self.shipment.holder_type)  # hàng vẫn ở Shop tới khi lấy

    def test_resend_returns_same_code_without_side_effects(self):
        """BR1, BR2: gửi lại (kể cả với phiên bản cũ đã tải trước khi duyệt) không sinh mã thứ hai."""
        old_version = self.version()
        code = self.approve(old_version).json()["tracking_code"]
        self.client.force_login(self.admin_2)
        again = self.approve(old_version)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["tracking_code"], code)
        self.assertEqual(ShipmentEvent.objects.filter(action=ShipmentAction.APPROVE_REQUEST).count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_shop_edited_after_staff_opened_is_conflict(self):
        """UC05.6 E1: không duyệt trên nội dung Shop vừa đổi."""
        seen = self.version()
        services.update_request(self.shop, self.shipment.pk, {"cod_amount": 999000},
                                Shipment.objects.get(pk=self.shipment.pk).updated_at)
        response = self.approve(seen)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"],
                         {"code": ErrorCode.CONFLICT, "message": STALE_FOR_DECISION_MESSAGE, "fields": {}})
        self.assertIsNone(Shipment.objects.get(pk=self.shipment.pk).tracking_code)
        self.assertEqual(self.approve().status_code, 200)  # tải lại rồi duyệt được

    def test_cannot_approve_cancelled_or_rejected(self):
        for status, label in [(ShipmentStatus.CANCELLED, "Đã hủy"), (ShipmentStatus.REJECTED, "Bị từ chối")]:
            with self.subTest(status=status):
                Shipment.objects.filter(pk=self.shipment.pk).update(status=status)
                response = self.approve()
                self.assertEqual(response.status_code, 409)
                error = response.json()["error"]
                self.assertEqual(error["code"], ErrorCode.INVALID_TRANSITION)
                self.assertEqual(error["message"], f"Yêu cầu đang ở trạng thái {label} nên không duyệt được.")
                self.assertIsNone(Shipment.objects.get(pk=self.shipment.pk).tracking_code)

    def test_missing_version(self):
        response = self.client.post(approve_url(self.shipment.pk), {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["fields"]["updated_at"], [MISSING_VERSION_MESSAGE])  # như PATCH
        self.assert_untouched()

    def test_code_collision_retries_then_succeeds(self):
        taken = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=taken.pk).update(tracking_code="HTT261121AAAAA")
        with mock.patch.object(services, "generate_tracking_code", side_effect=["HTT261121AAAAA", "HTT261121BBBBB"]):
            response = self.approve()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tracking_code"], "HTT261121BBBBB")

    def test_code_collision_exhausted_leaves_nothing(self):
        """Điều kiện sau UC05.6: lỗi thì không có vận đơn dở dang (không đổi trạng thái/lịch sử/thông báo)."""
        taken = make_shipment(self.shop, self.ward)
        Shipment.objects.filter(pk=taken.pk).update(tracking_code="HTT261121AAAAA")
        with mock.patch.object(services, "generate_tracking_code", return_value="HTT261121AAAAA") as gen:
            response = self.approve()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.SERVER_ERROR)
        self.assertEqual(gen.call_count, TRACKING_CODE_MAX_ATTEMPTS)
        self.assert_untouched()


class RejectTests(Base):
    def test_reject_with_reason(self):
        response = self.reject("  Địa chỉ giao không rõ số nhà  ")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data["status"], data["tracking_code"]), (ShipmentStatus.REJECTED, None))
        self.assertEqual(data["rejection_reason"], "Địa chỉ giao không rõ số nhà")
        self.assertEqual(data["allowed_actions"], [])

        event = ShipmentEvent.objects.get(shipment=self.shipment)
        self.assertEqual((event.action, event.actor, event.reason),
                         (ShipmentAction.REJECT_REQUEST, self.admin, "Địa chỉ giao không rõ số nhà"))
        notice = Notification.objects.get()
        self.assertEqual((notice.recipient, notice.kind), (self.shop, NotificationKind.REQUEST_REJECTED))
        self.assertEqual(notice.body, "Lý do: Địa chỉ giao không rõ số nhà")
        self.assertEqual(notice.payload, {"shipment_id": self.shipment.pk})

        self.client.force_login(self.shop)  # Shop thấy lý do ở chi tiết của mình
        detail = self.client.get(reverse("shipment-detail", args=[self.shipment.pk])).json()
        self.assertEqual(detail["rejection_reason"], "Địa chỉ giao không rõ số nhà")

    def test_reason_required_and_limited(self):
        for reason in ["", "   ", None, "x" * (EVENT_REASON_MAX_LENGTH + 1)]:
            with self.subTest(reason=reason if reason is None else len(reason)):
                body = {"updated_at": self.version()}
                if reason is not None:
                    body["reason"] = reason
                response = self.client.post(reject_url(self.shipment.pk), body, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("reason", response.json()["error"]["fields"])
        response = self.client.post(reject_url(self.shipment.pk), {"updated_at": self.version()},
                                    content_type="application/json")
        self.assertEqual(response.json()["error"]["fields"]["reason"], [REJECT_REASON_REQUIRED_MESSAGE])
        self.assert_untouched()

    def test_reject_twice_is_idempotent(self):
        old_version = self.version()
        self.assertEqual(self.reject("Lần 1", old_version).status_code, 200)
        again = self.reject("Lần 2", old_version)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["rejection_reason"], "Lần 1")
        self.assertEqual(ShipmentEvent.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_cannot_cross_decide(self):
        self.approve()
        response = self.reject()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["message"],
                         "Yêu cầu đang ở trạng thái Chờ lấy hàng nên không từ chối được.")

        other = make_shipment(self.shop, self.ward)
        services.reject_request(self.admin, other.pk, "Sai", Shipment.objects.get(pk=other.pk).updated_at)
        response = self.approve(shipment=other)
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(Shipment.objects.get(pk=other.pk).tracking_code)

    def test_stale_version_conflict(self):
        seen = self.version()
        services.update_request(self.shop, self.shipment.pk, {"note": "Shop sửa"},
                                Shipment.objects.get(pk=self.shipment.pk).updated_at)
        response = self.reject(version=seen)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.CONFLICT)


class PermissionTests(Base):
    def test_only_staff(self):
        for user in [self.shop, self.shipper]:
            self.client.force_login(user)
            for url in [approve_url(self.shipment.pk), reject_url(self.shipment.pk)]:
                with self.subTest(user=user.username, url=url):
                    body = {"reason": "x", "updated_at": self.version()}
                    response = self.client.post(url, body, content_type="application/json")
                    self.assertEqual(response.status_code, 403)
        self.assert_untouched()

    def test_not_found_and_temp_password(self):
        self.assertEqual(self.client.post(approve_url(999999), {}, content_type="application/json").status_code, 404)
        self.admin.must_change_password = True
        self.admin.save(update_fields=["must_change_password"])
        response = self.approve()
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PASSWORD_CHANGE_REQUIRED)
        self.assert_untouched()

    def test_anonymous(self):
        self.client.logout()
        self.assertEqual(self.approve(version="2026-11-21T00:00:00Z").status_code, 401)


class ConcurrencyTests(RaceMixin, TransactionTestCase):
    """Hai thao tác thật chạy song song trên cùng đơn: bên đầu giữ khóa, bên sau phải đợi rồi thấy kết quả mới."""

    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.admin_2 = make_user("nv_b", "0900000005", UserRole.ADMIN)
        self.shipment = make_shipment(self.shop, make_ward())
        self.version = Shipment.objects.get(pk=self.shipment.pk).updated_at

    def approve_as(self, staff):
        return lambda: services.approve_request(staff, self.shipment.pk, self.version)

    def test_two_staff_approve_same_request_one_code(self):
        self.assertEqual(self.race(self.approve_as(self.admin), self.approve_as(self.admin_2)), "ok")
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        self.assertRegex(shipment.tracking_code, TRACKING_CODE_REGEX)
        self.assertEqual(ShipmentEvent.objects.filter(action=ShipmentAction.APPROVE_REQUEST).count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_approve_then_shop_cancel(self):
        outcome = self.race(self.approve_as(self.admin), lambda: services.cancel_request(self.shop, self.shipment.pk))
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).status, ShipmentStatus.AWAITING_PICKUP)

    def test_shop_cancel_then_approve(self):
        outcome = self.race(lambda: services.cancel_request(self.shop, self.shipment.pk), self.approve_as(self.admin))
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        self.assertEqual((shipment.status, shipment.tracking_code), (ShipmentStatus.CANCELLED, None))
        self.assertFalse(Notification.objects.exists())

    def test_shop_update_then_approve_on_old_version(self):
        outcome = self.race(
            lambda: services.update_request(self.shop, self.shipment.pk, {"cod_amount": 1}, self.version),
            self.approve_as(self.admin),
        )
        self.assertEqual(outcome, ErrorCode.CONFLICT)
        self.assertIsNone(Shipment.objects.get(pk=self.shipment.pk).tracking_code)

    def test_approve_then_reject(self):
        outcome = self.race(
            self.approve_as(self.admin),
            lambda: services.reject_request(self.admin_2, self.shipment.pk, "Muộn", self.version),
        )
        self.assertEqual(outcome, ErrorCode.INVALID_TRANSITION)
        self.assertEqual(Shipment.objects.get(pk=self.shipment.pk).status, ShipmentStatus.AWAITING_PICKUP)
        self.assertFalse(ShipmentEvent.objects.filter(action=ShipmentAction.REJECT_REQUEST).exists())

    def test_tracking_code_unique_under_parallel_approvals_of_different_requests(self):
        """Nhiều đơn duyệt song song: mọi mã khác nhau và hợp lệ (unique DB là lớp chặn cuối)."""
        others = [make_shipment(self.shop, make_ward(code=f"W{i}", name=f"P{i}")) for i in range(5)]
        errors = []

        def approve(shipment):
            try:
                services.approve_request(self.admin, shipment.pk, Shipment.objects.get(pk=shipment.pk).updated_at)
            except Exception as exc:  # pragma: no cover
                errors.append(repr(exc))
            finally:
                connections.close_all()

        threads = [threading.Thread(target=approve, args=(s,)) for s in others]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertEqual(errors, [])
        codes = list(Shipment.objects.filter(pk__in=[s.pk for s in others]).values_list("tracking_code", flat=True))
        self.assertEqual(len(set(codes)), 5)
        self.assertTrue(all(re.match(TRACKING_CODE_REGEX, c) for c in codes))
