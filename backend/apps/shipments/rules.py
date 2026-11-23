"""Điều kiện phụ của hành động vận đơn, ngoài bảng SHIPMENT_TRANSITIONS (vai trò + trạng thái nguồn).

Một chỗ duy nhất cho cả nút hiển thị (`shipment_allowed_actions`) và service (kiểm khi thực hiện) — tránh
`if` rải rác trong serializer / view.
- Spec 007 D8: hết lượt giao thì không giao lại / phân công giao nữa.
- Spec 008 D3: phân công hoàn chỉ khi hàng đang ở Shipper; hàng đã ở điểm tập kết (UC06.7 A1.2) thì tiếp nhận
  thẳng, không tạo chuyến hoàn thừa.
"""
from apps.core.transitions import allowed_actions

from .constants import MAX_DELIVERY_ATTEMPTS, SHIPMENT_TRANSITIONS, HolderType, ShipmentAction, ShipmentStatus


def has_delivery_attempts_left(shipment):
    """Còn lượt giao thực tế (UC04.12 BR1, UC06.6 BR2) — tính cả lần thành công."""
    return shipment.delivery_attempts < MAX_DELIVERY_ATTEMPTS


def goods_with_shipper(shipment):
    """Hàng đang ở một Shipper — cần chuyến hoàn để đưa về điểm tập kết."""
    return shipment.holder_type == HolderType.SHIPPER


def return_receivable(shipment):
    """Tiếp nhận hàng hoàn: đang có chuyến hoàn, hoặc hàng đã nằm ở điểm tập kết (UC06.7 A1.2)."""
    return shipment.status == ShipmentStatus.RETURNING or shipment.holder_type == HolderType.HUB


# hành động -> hàm(shipment) trả True nếu được làm. Hành động không có ở đây: chỉ cần bảng trạng thái.
SHIPMENT_ACTION_GUARDS = {
    ShipmentAction.ASSIGN_DELIVERY: has_delivery_attempts_left,
    ShipmentAction.DECIDE_REDELIVERY: has_delivery_attempts_left,
    ShipmentAction.ASSIGN_RETURN: goods_with_shipper,  # spec 008
    ShipmentAction.RECEIVE_RETURN: return_receivable,
}


def guard_allows(shipment, action):
    return SHIPMENT_ACTION_GUARDS.get(action, lambda _shipment: True)(shipment)


def shipment_allowed_actions(shipment, role):
    """Hành động vai trò này được làm trên đơn lúc này (để hiện nút), đã sắp xếp."""
    return sorted(
        action for action in allowed_actions(SHIPMENT_TRANSITIONS, shipment.status, role)
        if guard_allows(shipment, action)
    )
