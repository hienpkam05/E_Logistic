"""Phạm vi dữ liệu vận đơn theo vai trò (phân quyền quy tắc 2, 8).

Mọi API vận đơn lấy queryset qua `shipments_visible_to` — spec sau mở rộng tại đây, không tạo API riêng theo vai trò.
"""
from apps.accounts.constants import UserRole

from .models import Shipment


def shipments_visible_to(user):
    """Shop: chỉ đơn của mình (spec 004). Nhân viên/Admin: toàn hệ thống (spec 005, UC05.9).

    Shipper (spec 006): đơn có nhiệm vụ được giao cho mình — dùng subquery (không JOIN + distinct) để vẫn
    `select_for_update()` được: PostgreSQL không cho FOR UPDATE cùng DISTINCT. Shipper vẫn KHÔNG gọi API vận đơn
    (quyền ở view); nhánh này cho phần dùng chung / spec sau.
    """
    if user.role == UserRole.SHOP:
        return Shipment.objects.filter(shop=user)
    if user.role == UserRole.ADMIN:
        return Shipment.objects.all()
    if user.role == UserRole.SHIPPER:
        from apps.dispatch.models import Task  # muộn: dispatch.models import shipments.models

        return Shipment.objects.filter(pk__in=Task.objects.filter(shipper=user).values("shipment_id"))
    return Shipment.objects.none()
