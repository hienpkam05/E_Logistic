"""Spec 005 Phase 2: Nhân viên xem danh sách / chi tiết / lịch sử toàn hệ thống; lọc ngày, sắp xếp, tìm theo Shop."""
from datetime import UTC, datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.shipments.constants import DATE_RANGE_INVALID_MESSAGE, ShipmentAction
from apps.shipments.models import Shipment

from .factories import make_shipment, make_user, make_ward

LIST = reverse("shipment-list")


def detail(pk):
    return reverse("shipment-detail", args=[pk])


class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop_a = make_user("shop_a", "0900000001", full_name="Tiệm Hoa Hồng")
        self.shop_b = make_user("shop_b", "0900000002", full_name="Shop Giày Bình")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("shipper_a", "0900000004", UserRole.SHIPPER)
        self.a1 = make_shipment(self.shop_a, self.ward)
        self.b1 = make_shipment(self.shop_b, self.ward, receiver_name="Lê Văn C")
        self.client.force_login(self.admin)

    def ids(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return [row["id"] for row in response.json()["results"]]

    def set_created(self, shipment, value):
        Shipment.objects.filter(pk=shipment.pk).update(created_at=value)


class AccessTests(Base):
    def test_staff_sees_every_shop_shop_sees_own(self):
        self.assertCountEqual(self.ids(self.client.get(LIST)), [self.a1.id, self.b1.id])
        row = next(r for r in self.client.get(LIST).json()["results"] if r["id"] == self.b1.id)
        self.assertEqual(row["shop"]["username"], "shop_b")
        self.client.force_login(self.shop_a)
        self.assertEqual(self.ids(self.client.get(LIST)), [self.a1.id])

    def test_staff_detail_and_events_of_any_shop(self):
        response = self.client.get(detail(self.b1.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["allowed_actions"],
                         [ShipmentAction.APPROVE_REQUEST, ShipmentAction.REJECT_REQUEST])
        # UC05.7 bước 4: người giữ hàng, số lần giao (chưa phát sinh → Shop giữ, 0 lần).
        self.assertEqual((response.json()["holder_type"], response.json()["delivery_attempts"]), ("SHOP", 0))
        self.assertEqual(self.client.get(reverse("shipment-events", args=[self.b1.pk])).status_code, 200)
        self.assertEqual(self.client.get(detail(999999)).json()["error"]["code"], ErrorCode.NOT_FOUND)

    def test_staff_cannot_write_shop_endpoints(self):
        """Nhân viên chỉ duyệt/từ chối, không tạo/sửa/hủy thay Shop (ngoài đặc tả)."""
        for method, url, body in [
            ("post", LIST, {}),
            ("patch", detail(self.a1.pk), {"note": "x", "updated_at": self.a1.updated_at.isoformat()}),
            ("post", reverse("shipment-cancel", args=[self.a1.pk]), {}),
        ]:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, body, content_type="application/json")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], ErrorCode.PERMISSION_DENIED)
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.note, "")

    def test_shipper_still_forbidden(self):
        self.client.force_login(self.shipper)
        for url in [LIST, detail(self.a1.pk), reverse("shipment-events", args=[self.a1.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_temp_password_staff_blocked(self):
        self.admin.must_change_password = True
        self.admin.save(update_fields=["must_change_password"])
        response = self.client.get(LIST)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PASSWORD_CHANGE_REQUIRED)


class FilterTests(Base):
    def test_date_range_uses_vietnam_day_inclusive(self):
        # 16:59 UTC ngày 20 = 23:59 giờ VN ngày 20; 17:00 UTC ngày 20 = 00:00 giờ VN ngày 21.
        self.set_created(self.a1, datetime(2026, 11, 20, 16, 59, tzinfo=UTC))
        self.set_created(self.b1, datetime(2026, 11, 20, 17, 0, tzinfo=UTC))
        self.assertEqual(self.ids(self.client.get(LIST, {"created_from": "2026-11-21"})), [self.b1.id])
        self.assertEqual(self.ids(self.client.get(LIST, {"created_to": "2026-11-20"})), [self.a1.id])
        both = {"created_from": "2026-11-20", "created_to": "2026-11-21"}
        self.assertCountEqual(self.ids(self.client.get(LIST, both)), [self.a1.id, self.b1.id])
        same_day = {"created_from": "2026-11-21", "created_to": "2026-11-21"}
        self.assertEqual(self.ids(self.client.get(LIST, same_day)), [self.b1.id])

    def test_invalid_dates(self):
        response = self.client.get(LIST, {"created_from": "2026-11-22", "created_to": "2026-11-21"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["fields"]["created_to"], [DATE_RANGE_INVALID_MESSAGE])
        response = self.client.get(LIST, {"created_from": "21/11/2026"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("created_from", response.json()["error"]["fields"])

    def test_ordering(self):
        self.set_created(self.a1, datetime(2026, 11, 20, 1, 0, tzinfo=UTC))
        self.set_created(self.b1, datetime(2026, 11, 21, 1, 0, tzinfo=UTC))
        self.assertEqual(self.ids(self.client.get(LIST)), [self.b1.id, self.a1.id])  # mặc định mới nhất trước
        self.assertEqual(self.ids(self.client.get(LIST, {"ordering": "created_at"})), [self.a1.id, self.b1.id])
        response = self.client.get(LIST, {"ordering": "shop"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("ordering", response.json()["error"]["fields"])

    def test_ordering_ties_broken_by_id(self):
        same = datetime(2026, 11, 21, 1, 0, tzinfo=UTC)
        self.set_created(self.a1, same)
        self.set_created(self.b1, same)
        self.assertEqual(self.ids(self.client.get(LIST, {"ordering": "created_at"})), [self.a1.id, self.b1.id])
        self.assertEqual(self.ids(self.client.get(LIST)), [self.b1.id, self.a1.id])

    def test_staff_search_by_shop_name_username_phone(self):
        for term in ["giày bình", "shop_b", "0900000002", "Lê Văn"]:
            with self.subTest(term=term):
                self.assertEqual(self.ids(self.client.get(LIST, {"q": term})), [self.b1.id])

    def test_shop_search_does_not_match_shop_fields(self):
        """Shop không tìm theo thông tin Shop (luôn là chính mình) — tránh "tìm tên mình ra tất cả"."""
        self.client.force_login(self.shop_a)
        self.assertEqual(self.ids(self.client.get(LIST, {"q": "Hoa Hồng"})), [])
        self.assertEqual(self.ids(self.client.get(LIST, {"q": "shop_b"})), [])

    def test_status_filter_with_ordering_for_pending_tab(self):
        Shipment.objects.filter(pk=self.b1.pk).update(status="CANCELLED")
        response = self.client.get(LIST, {"status": "PENDING_APPROVAL", "ordering": "created_at"})
        self.assertEqual(self.ids(response), [self.a1.id])


class QueryCountTests(Base):
    def test_staff_list_constant_queries_across_shops(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(LIST).status_code, 200)
            return len(ctx.captured_queries)

        baseline = count()
        for i in range(5):
            shop = make_user(f"shop_x{i}", f"09100000{i:02d}")
            make_shipment(shop, self.ward)
        self.assertEqual(count(), baseline)
