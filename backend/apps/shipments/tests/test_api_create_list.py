"""Spec 004 Phase 2: tạo yêu cầu, danh sách, chi tiết, danh mục phường/xã."""
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.errors import ErrorCode
from apps.shipments.constants import COD_MAX_VND, WARD_NOT_IN_HANOI_MESSAGE, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent

from .factories import make_shipment, make_user, make_ward

LIST, WARDS = reverse("shipment-list"), reverse("ward-list")
DETAIL_FIELDS = {
    "id", "request_code", "tracking_code", "status", "sender_name", "sender_phone", "pickup_ward", "pickup_address",
    "receiver_name", "receiver_phone", "delivery_ward", "delivery_address", "package_description", "package_count",
    "weight_grams", "cod_amount", "note", "created_at", "updated_at", "allowed_actions",
    "shop", "rejection_reason", "holder_type", "delivery_attempts",  # spec 005
    "delivery",  # spec 007: kết quả giao thành công (null khi chưa giao)
    "return_result",  # spec 008: Shop đã nhận lại hàng hoàn (null khi chưa)
}
SUMMARY_FIELDS = {"id", "request_code", "tracking_code", "status", "shop", "receiver_name", "receiver_phone",
                  "delivery_ward", "cod_amount", "created_at"}


def detail(pk):
    return reverse("shipment-detail", args=[pk])


class Base(TestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.shop_b = make_user("shop_b", "0900000002")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("shipper_a", "0900000004", UserRole.SHIPPER)
        self.ward_hk = make_ward("00070", "Phường Hoàn Kiếm")
        self.ward_bd = make_ward("00160", "Phường Ba Đình")
        self.ward_old = make_ward("00999", "Phường Cũ", is_active=False)
        self.client.force_login(self.shop)

    def payload(self, **extra):
        data = {
            "sender_name": "Shop Hoa An", "sender_phone": "0901234567",
            "pickup_ward": "00070", "pickup_address": "12 Hàng Bạc",
            "receiver_name": "Trần Thị B", "receiver_phone": "0912345678",
            "delivery_ward": "00160", "delivery_address": "5 Đội Cấn",
            "package_description": "Áo thun", "package_count": 2, "weight_grams": 800,
            "cod_amount": 350000, "note": "Gọi trước khi giao",
        }
        data.update(extra)
        return {k: v for k, v in data.items() if v is not ...}

    def create(self, client=None, **extra):
        return (client or self.client).post(LIST, self.payload(**extra), content_type="application/json")

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        body = response.json()["error"]
        self.assertEqual(body["code"], code)
        return body


class WardTests(Base):
    def test_active_only_sorted_by_name_no_pagination(self):
        body = self.client.get(WARDS).json()
        self.assertEqual(body, [{"code": "00160", "name": "Phường Ba Đình"},
                                {"code": "00070", "name": "Phường Hoàn Kiếm"}])

    def test_any_logged_in_role_but_not_anonymous(self):
        for user in (self.admin, self.shipper):
            client = Client()
            client.force_login(user)
            self.assertEqual(client.get(WARDS).status_code, 200)
        self.client.logout()
        self.assert_error(self.client.get(WARDS), 401, ErrorCode.NOT_AUTHENTICATED)


class CreateTests(Base):
    def test_create_full(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(set(body), DETAIL_FIELDS)
        shipment = Shipment.objects.get()
        self.assertEqual(body["request_code"], f"YC{shipment.pk:08d}")
        self.assertIsNone(body["tracking_code"])  # BR1: chỉ duyệt mới có mã vận đơn
        self.assertEqual(body["status"], ShipmentStatus.PENDING_APPROVAL)
        self.assertEqual(body["pickup_ward"], {"code": "00070", "name": "Phường Hoàn Kiếm"})
        self.assertEqual(body["allowed_actions"], [ShipmentAction.CANCEL_REQUEST, ShipmentAction.UPDATE_REQUEST])
        self.assertEqual(shipment.shop, self.shop)
        event = ShipmentEvent.objects.get()
        self.assertEqual((event.action, event.from_status, event.to_status, event.actor),
                         (ShipmentAction.CREATE_REQUEST, None, ShipmentStatus.PENDING_APPROVAL, self.shop))

    def test_optional_fields(self):
        response = self.create(weight_grams=..., note=..., cod_amount=0)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()["weight_grams"])
        self.assertEqual(response.json()["note"], "")

    def test_forbidden_fields_ignored(self):
        response = self.create(shop=self.shop_b.pk, status="DELIVERED", tracking_code="HTT-GIA",
                               request_code="YC99999999", holder_type="HUB", delivery_attempts=3)
        body = response.json()
        shipment = Shipment.objects.get()
        self.assertEqual(shipment.shop, self.shop)  # phân quyền mục 6
        self.assertEqual((body["status"], body["tracking_code"]), (ShipmentStatus.PENDING_APPROVAL, None))
        self.assertNotEqual(body["request_code"], "YC99999999")
        self.assertEqual((shipment.holder_type, shipment.delivery_attempts), ("SHOP", 0))

    def test_invalid_fields_create_nothing(self):
        cases = {
            "receiver_name": {"receiver_name": ""},
            "receiver_phone": {"receiver_phone": "123"},
            "sender_phone": {"sender_phone": "1900abc"},
            "pickup_address": {"pickup_address": "   "},
            "package_description": {"package_description": ""},
            "package_count": {"package_count": 0},
            "weight_grams": {"weight_grams": 100_001},
            "cod_amount": {"cod_amount": -1},
        }
        for field, extra in cases.items():
            with self.subTest(field=field):
                err = self.assert_error(self.create(**extra), 400, ErrorCode.VALIDATION_ERROR)
                self.assertIn(field, err["fields"])
        err = self.assert_error(self.create(cod_amount=COD_MAX_VND + 1), 400, ErrorCode.VALIDATION_ERROR)
        self.assertIn("cod_amount", err["fields"])
        self.assertFalse(Shipment.objects.exists())
        self.assertFalse(ShipmentEvent.objects.exists())

    def test_missing_required_fields(self):
        err = self.assert_error(self.client.post(LIST, {}, content_type="application/json"), 400,
                                ErrorCode.VALIDATION_ERROR)
        self.assertEqual(set(err["fields"]), {
            "sender_name", "sender_phone", "pickup_ward", "pickup_address", "receiver_name", "receiver_phone",
            "delivery_ward", "delivery_address", "package_description",
        })

    def test_ward_outside_list_or_inactive(self):
        for field, code in (("pickup_ward", "KHONG-CO"), ("delivery_ward", "00999")):
            with self.subTest(field=field):
                err = self.assert_error(self.create(**{field: code}), 400, ErrorCode.VALIDATION_ERROR)
                self.assertEqual(err["fields"][field], [WARD_NOT_IN_HANOI_MESSAGE])

    def test_only_shop_can_create(self):
        for user in (self.admin, self.shipper):
            client = Client()
            client.force_login(user)
            self.assert_error(self.create(client=client), 403, ErrorCode.PERMISSION_DENIED)
        self.assertFalse(Shipment.objects.exists())

    def test_sender_snapshot_not_linked_to_profile(self):
        self.create(sender_name="Tên trên đơn")
        self.shop.full_name = "Tên hồ sơ mới"
        self.shop.save()
        self.assertEqual(Shipment.objects.get().sender_name, "Tên trên đơn")  # UC02.2 BR2


class ListDetailTests(Base):
    def setUp(self):
        super().setUp()
        self.mine = [make_shipment(self.shop, self.ward_hk, receiver_name=f"Khách {i}") for i in range(3)]
        Shipment.objects.filter(pk=self.mine[0].pk).update(status=ShipmentStatus.CANCELLED)
        Shipment.objects.filter(pk=self.mine[1].pk).update(status=ShipmentStatus.AWAITING_PICKUP,
                                                           tracking_code="HTT261121ABCDE")
        self.theirs = make_shipment(self.shop_b, self.ward_hk, receiver_name="Khách của B")

    def ids(self, **params):
        return [s["id"] for s in self.client.get(LIST, params).json()["results"]]

    def test_only_mine_newest_first(self):
        body = self.client.get(LIST).json()
        self.assertEqual(body["count"], 3)
        self.assertEqual([s["id"] for s in body["results"]], [s.pk for s in reversed(self.mine)])
        self.assertEqual(set(body["results"][0]), SUMMARY_FIELDS)

    def test_pending_shows_request_code_approved_shows_tracking_code(self):
        rows = {s["id"]: s for s in self.client.get(LIST).json()["results"]}
        self.assertIsNone(rows[self.mine[2].pk]["tracking_code"])
        self.assertEqual(rows[self.mine[1].pk]["tracking_code"], "HTT261121ABCDE")

    def test_status_filter_single_and_multiple(self):
        self.assertEqual(self.ids(status="CANCELLED"), [self.mine[0].pk])
        self.assertEqual(set(self.ids(status=["CANCELLED", "PENDING_APPROVAL"])), {self.mine[0].pk, self.mine[2].pk})
        err = self.assert_error(self.client.get(LIST, {"status": "KHONG_CO"}), 400, ErrorCode.VALIDATION_ERROR)
        self.assertIn("status", err["fields"])

    def test_search_by_codes_and_receiver(self):
        self.assertEqual(self.ids(q="abcde"), [self.mine[1].pk])
        self.assertEqual(self.ids(q=self.mine[2].request_code.lower()), [self.mine[2].pk])
        self.assertEqual(self.ids(q="khách 0"), [self.mine[0].pk])
        self.assertEqual(self.ids(q="0912345678"), self.ids())
        self.assertEqual(self.ids(q="Khách của B"), [])  # BR1: bộ lọc vẫn giới hạn theo Shop

    def test_detail_own_and_allowed_actions(self):
        body = self.client.get(detail(self.mine[2].pk)).json()
        self.assertEqual(set(body), DETAIL_FIELDS)
        self.assertEqual(body["allowed_actions"], ["CANCEL_REQUEST", "UPDATE_REQUEST"])
        self.assertEqual(self.client.get(detail(self.mine[1].pk)).json()["allowed_actions"], [])

    def test_other_shop_404_same_as_missing(self):
        """Shop A đổi id trên URL để đọc đơn Shop B (phân quyền mục 6)."""
        a = self.client.get(detail(self.theirs.pk))
        b = self.client.get(detail(999999))
        self.assert_error(a, 404, ErrorCode.NOT_FOUND)
        self.assertEqual(a.json(), b.json())
        self.assertNotIn("Khách của B", a.content.decode())

    def test_shipper_forbidden(self):
        """Spec 005 mở quyền XEM cho Nhân viên (test_staff_list.py); Shipper vẫn 403 tới spec 006."""
        client = Client()
        client.force_login(self.shipper)
        for url in (LIST, detail(self.mine[0].pk)):
            with self.subTest(url=url):
                self.assert_error(client.get(url), 403, ErrorCode.PERMISSION_DENIED)

    def test_temp_password_and_anonymous(self):
        self.client.logout()
        self.assert_error(self.client.get(LIST), 401, ErrorCode.NOT_AUTHENTICATED)
        self.shop.must_change_password = True
        self.shop.save()
        self.client.force_login(self.shop)
        self.assert_error(self.client.get(LIST), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)

    def test_no_delete(self):
        self.assert_error(self.client.delete(detail(self.mine[2].pk)), 405, ErrorCode.REQUEST_ERROR)

    def test_query_count_constant(self):
        def count(url):
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(url).status_code, 200)
            return len(ctx)

        few = count(LIST)
        for i in range(25):
            make_shipment(self.shop, self.ward_bd)
        self.assertEqual(count(LIST), few)
        self.assertEqual(count(detail(self.mine[2].pk)), count(detail(self.mine[1].pk)))

    def test_pagination(self):
        for _ in range(25):
            make_shipment(self.shop, self.ward_bd)
        body = self.client.get(LIST, {"page": 2}).json()
        self.assertEqual((body["count"], len(body["results"])), (28, 8))
