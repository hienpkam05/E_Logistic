"""Spec 008 Phase 1: ràng buộc DB của bàn giao hàng hoàn, cấu hình điểm tập kết, danh mục mới."""
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.dispatch.constants import RECEIVER_NAME_MAX_LENGTH, HandoverKind
from apps.dispatch.models import Handover
from apps.notifications.constants import NotificationKind
from apps.shipments.constants import ShipmentAction
from apps.shipments.tests.factories import make_shipment, make_user, make_ward


class HandoverReceiverTests(TestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.shipment = make_shipment(self.shop, make_ward())

    def handover(self, kind, **extra):
        return Handover.objects.create(shipment=self.shipment, kind=kind, received_by=self.admin, **extra)

    def assert_rejected(self, fn):
        with self.assertRaises(IntegrityError), transaction.atomic():
            fn()

    def test_shop_pickup_requires_receiver_name(self):
        """D7 (UC04.11 bước 6): lưu người nhận phía Shop — thiếu / rỗng bị DB chặn."""
        self.assert_rejected(lambda: self.handover(HandoverKind.SHOP_PICKUP))
        self.assert_rejected(lambda: self.handover(HandoverKind.SHOP_PICKUP, receiver_name=""))
        handover = self.handover(HandoverKind.SHOP_PICKUP, receiver_name="Nguyễn Văn Hoa")
        self.assertEqual(handover.receiver_name, "Nguyễn Văn Hoa")

    def test_other_kinds_have_no_receiver_name(self):
        for kind in (HandoverKind.HUB_INTAKE, HandoverKind.RETURN_INTAKE):
            with self.subTest(kind):
                self.assert_rejected(lambda: self.handover(kind, receiver_name="Ai đó"))
                self.handover(kind, from_shipper=self.shipper)

    def test_new_kinds_and_length(self):
        self.assertEqual(HandoverKind.values, ["HUB_INTAKE", "RETURN_INTAKE", "SHOP_PICKUP"])
        self.assertEqual(Handover._meta.get_field("receiver_name").max_length, RECEIVER_NAME_MAX_LENGTH)
        self.assert_rejected(lambda: self.handover("UNKNOWN"))  # CHECK kind tạo lại vẫn chặn mã lạ


class CatalogTests(TestCase):
    def test_new_codes(self):
        self.assertIn("REPORT_RETURN_HANDOVER", ShipmentAction.values)
        self.assertIn("REPORT_RETURN_ISSUE", ShipmentAction.values)
        self.assertIn("RETURN_HANDOVER_REPORTED", NotificationKind.values)

    @override_settings(HUB={"name": "Kho Cầu Giấy", "address": "12 Xuân Thủy", "phone": "0241234567"})
    def test_meta_exposes_hub_from_settings(self):
        """D6: điểm tập kết lấy từ cấu hình (.env), một nguồn cho Shipper và Shop."""
        hub = self.client.get(reverse("meta-choices")).json()["hub"]
        self.assertEqual(hub, {"name": "Kho Cầu Giấy", "address": "12 Xuân Thủy", "phone": "0241234567"})

    def test_meta_hub_default_has_all_fields(self):
        hub = self.client.get(reverse("meta-choices")).json()["hub"]
        self.assertEqual(set(hub), {"name", "address", "phone"})
        self.assertTrue(all(hub.values()))
