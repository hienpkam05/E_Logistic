"""Spec 005 Phase 1: mã vận đơn, phạm vi dữ liệu theo vai trò, serializer cho Nhân viên."""
import re
from datetime import UTC, datetime

from django.test import RequestFactory, TestCase

from apps.accounts.constants import UserRole
from apps.shipments import constants as c
from apps.shipments.constants import ShipmentAction, ShipmentStatus
from apps.shipments.models import ShipmentEvent
from apps.shipments.permissions import shipments_visible_to
from apps.shipments.serializers import ShipmentDetailSerializer, ShipmentSummarySerializer
from apps.shipments.services import generate_tracking_code

from .factories import make_shipment, make_user, make_ward


class TrackingCodeTests(TestCase):
    def test_format_and_alphabet(self):
        codes = [generate_tracking_code() for _ in range(300)]
        for code in codes:
            self.assertRegex(code, c.TRACKING_CODE_REGEX)
            self.assertFalse(set("IO01") & set(code[-c.TRACKING_CODE_RANDOM_LENGTH:]))
        # 32^5 ≈ 33 triệu tổ hợp: 300 mã gần như không trùng — bắt lỗi "phần ngẫu nhiên cố định".
        self.assertGreater(len(set(codes)), 295)

    def test_date_is_vietnam_time_around_utc_midnight(self):
        # 16:59 UTC ngày 20 = 23:59 giờ VN ngày 20; 17:00 UTC = 00:00 ngày 21 giờ VN.
        self.assertTrue(generate_tracking_code(datetime(2026, 11, 20, 16, 59, tzinfo=UTC)).startswith("HTT261120"))
        self.assertTrue(generate_tracking_code(datetime(2026, 11, 20, 17, 0, tzinfo=UTC)).startswith("HTT261121"))

    def test_fits_db_column(self):
        from apps.shipments.models import Shipment

        self.assertLessEqual(len(generate_tracking_code()), Shipment._meta.get_field("tracking_code").max_length)

    def test_regex_rejects_bad_codes(self):
        for bad in ["HTT26112K7Q2M", "HTT261121K7Q2", "HTT261121K7Q2O", "XYZ261121K7Q2M", "HTT261121k7q2m"]:
            self.assertIsNone(re.match(c.TRACKING_CODE_REGEX, bad), bad)


class Base(TestCase):
    def setUp(self):
        self.ward = make_ward()
        self.shop_a = make_user("shop_a", "0900000001")
        self.shop_b = make_user("shop_b", "0900000002")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("shipper_a", "0900000004", UserRole.SHIPPER)
        self.a1 = make_shipment(self.shop_a, self.ward)
        self.a2 = make_shipment(self.shop_a, self.ward)
        self.b1 = make_shipment(self.shop_b, self.ward)

    def context(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return {"request": request}


class ScopeTests(Base):
    def test_each_role(self):
        ids = lambda user: set(shipments_visible_to(user).values_list("id", flat=True))  # noqa: E731
        self.assertEqual(ids(self.shop_a), {self.a1.id, self.a2.id})
        self.assertEqual(ids(self.shop_b), {self.b1.id})
        self.assertEqual(ids(self.admin), {self.a1.id, self.a2.id, self.b1.id})  # UC05.9: toàn hệ thống
        self.assertEqual(ids(self.shipper), set())  # spec 006 mới mở


class SerializerTests(Base):
    def test_shop_block_has_contact_but_no_secret_fields(self):
        data = ShipmentSummarySerializer(self.b1, context=self.context(self.admin)).data
        self.assertEqual(data["shop"], {"id": self.shop_b.id, "username": "shop_b", "full_name": "Tên shop_b",
                                        "phone": "0900000002"})

    def test_allowed_actions_follow_viewer_role(self):
        as_admin = ShipmentDetailSerializer(self.a1, context=self.context(self.admin)).data
        as_shop = ShipmentDetailSerializer(self.a1, context=self.context(self.shop_a)).data
        self.assertEqual(as_admin["allowed_actions"], [ShipmentAction.APPROVE_REQUEST, ShipmentAction.REJECT_REQUEST])
        self.assertEqual(as_shop["allowed_actions"], [ShipmentAction.CANCEL_REQUEST, ShipmentAction.UPDATE_REQUEST])

    def test_rejection_reason_latest_and_only_when_rejected(self):
        ctx = self.context(self.shop_a)
        self.assertIsNone(ShipmentDetailSerializer(self.a1, context=ctx).data["rejection_reason"])
        for reason in ["Lần đầu", "Thiếu số nhà"]:
            ShipmentEvent.objects.create(shipment=self.a1, action=ShipmentAction.REJECT_REQUEST, actor=self.admin,
                                         from_status=ShipmentStatus.PENDING_APPROVAL,
                                         to_status=ShipmentStatus.REJECTED, reason=reason)
        # Còn Chờ xác nhận thì không trả lý do dù lịch sử có (không lộ lý do cũ sai ngữ cảnh).
        self.assertIsNone(ShipmentDetailSerializer(self.a1, context=ctx).data["rejection_reason"])
        self.a1.status = ShipmentStatus.REJECTED
        self.assertEqual(ShipmentDetailSerializer(self.a1, context=ctx).data["rejection_reason"], "Thiếu số nhà")

    def test_no_extra_query_unless_rejected(self):
        from apps.shipments.models import Shipment

        # Như shipments.views.detail_response cho Nhân viên: prefetch nhiệm vụ (spec 006) — vẫn 0 truy vấn thêm.
        shipment = (Shipment.objects.select_related("shop", "pickup_ward", "delivery_ward", "holder_shipper")
                    .prefetch_related("tasks").get(pk=self.a1.pk))
        with self.assertNumQueries(0):
            ShipmentDetailSerializer(shipment, context=self.context(self.admin)).data  # noqa: B018
