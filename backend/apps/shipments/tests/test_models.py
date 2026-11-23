from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.shipments.constants import COD_MAX_VND, HolderType, ShipmentAction, ShipmentStatus
from apps.shipments.models import Shipment, ShipmentEvent

from .factories import make_shipment, make_user, make_ward, shipment_data


class ShipmentModelTests(TestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.ward = make_ward()

    def create(self, **extra):
        return Shipment.objects.create(shop=self.shop, **shipment_data(self.ward, self.ward, **extra))

    def test_defaults(self):
        shipment = make_shipment(self.shop, self.ward)
        self.assertEqual(shipment.status, ShipmentStatus.PENDING_APPROVAL)
        self.assertEqual(shipment.holder_type, HolderType.SHOP)
        self.assertEqual(shipment.delivery_attempts, 0)
        self.assertIsNone(shipment.tracking_code)
        self.assertEqual(shipment.request_code, f"YC{shipment.pk:08d}")
        self.assertEqual(shipment.display_code, shipment.request_code)

    def test_display_code_prefers_tracking_code(self):
        shipment = make_shipment(self.shop, self.ward)
        shipment.tracking_code = "HTT261121K7Q2M"
        self.assertEqual(shipment.display_code, "HTT261121K7Q2M")

    def test_db_constraints(self):
        cases = {
            "cod âm": {"cod_amount": -1},
            "cod quá trần": {"cod_amount": COD_MAX_VND + 1},
            "số kiện 0": {"package_count": 0},
            "số kiện 100": {"package_count": 100},
            "khối lượng 0": {"weight_grams": 0},
            "khối lượng quá lớn": {"weight_grams": 100_001},
            "SĐT người nhận sai": {"receiver_phone": "123"},
            "SĐT người gửi sai": {"sender_phone": "09abc"},
            "trạng thái lạ": {"status": "KHONG_CO"},
            "nơi giữ hàng lạ": {"holder_type": "KHO"},
            "mã yêu cầu sai dạng": {"request_code": "XX123"},
        }
        for label, extra in cases.items():
            with self.subTest(label), self.assertRaises(IntegrityError), transaction.atomic():
                self.create(**extra)
        self.assertFalse(Shipment.objects.exists())

    def test_boundaries_ok(self):
        self.create(cod_amount=COD_MAX_VND, package_count=99, weight_grams=None)
        self.create(cod_amount=0, package_count=1, weight_grams=100_000)
        self.assertEqual(Shipment.objects.count(), 2)

    def test_request_and_tracking_codes_unique(self):
        a = make_shipment(self.shop, self.ward)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create(request_code=a.request_code)
        Shipment.objects.filter(pk=a.pk).update(tracking_code="HTT1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create(tracking_code="HTT1")

    def test_protect_shop_ward_and_history(self):
        shipment = make_shipment(self.shop, self.ward)
        ShipmentEvent.objects.create(shipment=shipment, action=ShipmentAction.CREATE_REQUEST,
                                     to_status=ShipmentStatus.PENDING_APPROVAL, actor=self.shop)
        for obj in (self.ward, self.shop, shipment):
            with self.subTest(obj=type(obj).__name__), self.assertRaises(ProtectedError):
                obj.delete()

    def test_list_order_newest_first(self):
        first = make_shipment(self.shop, self.ward)
        second = make_shipment(self.shop, self.ward)
        self.assertEqual(list(Shipment.objects.all()), [second, first])
