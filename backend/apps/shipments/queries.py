"""Truy vấn đọc cho tra cứu/lịch sử (spec 010). Dùng chung giữa API và đo EXPLAIN, không đổi dữ liệu."""
from django.db.models import Subquery
from .constants import REQUEST_CODE_PREFIX
from .models import Shipment
from .permissions import shipments_visible_to


def lookup_shipments(user, code):
    """code đã chuẩn hóa; lọc phạm vi trước, tìm đúng để dùng index unique hiện có."""
    # Prefix YC/HTT không trùng nhau; một cột unique chỉ có tối đa một kết quả.
    # Scalar subquery là InitPlan tìm mã một lần, sau đó lọc pk + quyền, tránh quét toàn Shop
    # khi thống kê shop chưa cập nhật. Không trả thông tin từ tập chưa lọc quyền.
    field = "request_code" if code.startswith(REQUEST_CODE_PREFIX) else "tracking_code"
    match = Shipment.objects.filter(**{field: code}).order_by().values("pk")[:1]
    return (shipments_visible_to(user).select_related("shop", "delivery_ward")
            .filter(pk=Subquery(match)).order_by())


def pickup_numbers(shipment):
    """Số thứ tự đợt nhiệm vụ lấy trên toàn đơn, không phụ thuộc phân trang/sắp xếp các mốc."""
    from apps.dispatch.constants import TaskType

    ids = shipment.tasks.filter(type=TaskType.PICKUP).order_by("assigned_at", "id").values_list("id", flat=True)
    return {task_id: number for number, task_id in enumerate(ids, start=1)}
