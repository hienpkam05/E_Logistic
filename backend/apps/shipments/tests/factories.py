"""Dữ liệu dùng chung cho test vận đơn."""
from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.shipments.models import Shipment, Ward

PASSWORD = "Matkhau@12345"


def make_user(username, phone, role=UserRole.SHOP, **extra):
    extra.setdefault("full_name", f"Tên {username}")
    return User.objects.create_user(username=username, password=PASSWORD, phone=phone, role=role, **extra)


def make_ward(code="W01", name="Phường Thử", **extra):
    return Ward.objects.create(code=code, name=name, **extra)


def shipment_data(pickup_ward, delivery_ward, **extra):
    return {
        "sender_name": "Shop Hoa An", "sender_phone": "0901234567",
        "pickup_ward": pickup_ward, "pickup_address": "12 Hàng Bạc",
        "receiver_name": "Trần Thị B", "receiver_phone": "0912345678",
        "delivery_ward": delivery_ward, "delivery_address": "5 Đội Cấn",
        "package_description": "Áo thun", "package_count": 2, "weight_grams": 800,
        "cod_amount": 350000, **extra,
    }


def make_shipment(shop, ward, **extra):
    shipment = Shipment.objects.create(shop=shop, **shipment_data(ward, ward, **extra))
    shipment.request_code = Shipment.build_request_code(shipment.pk)
    shipment.save(update_fields=["request_code"])
    return shipment
