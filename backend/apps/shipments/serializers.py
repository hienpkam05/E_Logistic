from rest_framework import serializers

from apps.accounts.constants import UserRole
from apps.accounts.serializers import EventActorSerializer
from apps.core.constants import SEARCH_QUERY_MAX_LENGTH

from .constants import (
    CANCEL_REASON_MAX_LENGTH,
    DATE_RANGE_INVALID_MESSAGE,
    DEFAULT_SHIPMENT_ORDERING,
    EVENT_REASON_MAX_LENGTH,
    MISSING_VERSION_MESSAGE,
    REJECT_REASON_REQUIRED_MESSAGE,
    SHIPMENT_LIST_ORDERINGS,
    WARD_NOT_IN_HANOI_MESSAGE,
    HolderType,
    ShipmentAction,
    ShipmentStatus,
)
from .models import Shipment, ShipmentEvent, Ward
from .rules import shipment_allowed_actions


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ["code", "name"]
        read_only_fields = fields


class ActiveWardField(serializers.SlugRelatedField):
    """Nhận mã phường/xã; chỉ chấp nhận phường đang dùng (spec 004 D1)."""

    default_error_messages = {
        "does_not_exist": WARD_NOT_IN_HANOI_MESSAGE,
        "invalid": WARD_NOT_IN_HANOI_MESSAGE,
    }

    def __init__(self, **kwargs):
        super().__init__(slug_field="code", queryset=Ward.objects.filter(is_active=True), **kwargs)


# Trường nội dung Shop nhập (tạo + sửa). Không có shop/mã/trạng thái/holder — các trường đó không nhận từ client.
CONTENT_FIELDS = [
    "sender_name", "sender_phone", "pickup_ward", "pickup_address",
    "receiver_name", "receiver_phone", "delivery_ward", "delivery_address",
    "package_description", "package_count", "weight_grams", "cod_amount", "note",
]


class ShipmentWriteSerializer(serializers.ModelSerializer):
    pickup_ward = ActiveWardField()
    delivery_ward = ActiveWardField()

    class Meta:
        model = Shipment
        fields = CONTENT_FIELDS
        extra_kwargs = {"weight_grams": {"required": False}, "note": {"required": False}}


class ShipmentShopSerializer(EventActorSerializer):
    """Shop của đơn — Nhân viên cần biết ai gửi để duyệt/liên hệ (UC05.7 bước 3, UC05.9 bước 3)."""

    class Meta(EventActorSerializer.Meta):
        fields = [*EventActorSerializer.Meta.fields, "phone"]
        read_only_fields = fields


class ShipmentSummarySerializer(serializers.ModelSerializer):
    """Một dòng danh sách (UC05.3, UC05.9). Queryset phải select_related("shop", "delivery_ward")."""

    shop = ShipmentShopSerializer(read_only=True)
    delivery_ward = WardSerializer(read_only=True)

    class Meta:
        model = Shipment
        fields = ["id", "request_code", "tracking_code", "status", "shop", "receiver_name", "receiver_phone",
                  "delivery_ward", "cod_amount", "created_at"]
        read_only_fields = fields


class ShipmentLookupSerializer(ShipmentSummarySerializer):
    """Tóm tắt tra cứu kèm cập nhật gần nhất; không đổi hợp đồng danh sách hiện có."""

    class Meta(ShipmentSummarySerializer.Meta):
        fields = [*ShipmentSummarySerializer.Meta.fields, "updated_at"]
        read_only_fields = fields


class ShipmentLookupQuerySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=SEARCH_QUERY_MAX_LENGTH)

    def validate_code(self, value):
        # CharField đã trim đầu/cuối. Không xóa khoảng trắng ở giữa, không tìm gần đúng/iexact.
        return value.upper()


class ShipmentEventQuerySerializer(serializers.Serializer):
    # Cùng quy tắc thời gian tạo + id với danh sách vận đơn, không lặp lại bảng sắp xếp.
    ordering = serializers.ChoiceField(choices=list(SHIPMENT_LIST_ORDERINGS), default=DEFAULT_SHIPMENT_ORDERING)

    def to_internal_value(self, data):
        # QueryDict/HTML có thể coi "ordering=" là bỏ tham số khi field có default.
        # Giữ rỗng là giá trị không hợp lệ; chỉ vắng hẳn key mới dùng thứ tự mặc định.
        return super().to_internal_value(dict(data.items()))


class ShipmentDetailSerializer(serializers.ModelSerializer):
    """Chi tiết (UC05.4, UC05.7).

    `allowed_actions`: hành động **vai trò người xem** được làm ở trạng thái hiện tại (Shop: sửa/hủy;
    Nhân viên: duyệt/từ chối…). `rejection_reason`: lý do của lần từ chối (spec 005 D5) — đọc từ lịch sử,
    chỉ truy vấn khi đơn đang Bị từ chối.
    """

    shop = ShipmentShopSerializer(read_only=True)
    pickup_ward = WardSerializer(read_only=True)
    delivery_ward = WardSerializer(read_only=True)
    allowed_actions = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    # Spec 006 — chỉ Nhân viên (quyền tối thiểu: Shop không thấy Shipper/nhiệm vụ nội bộ).
    holder_shipper = ShipmentShopSerializer(read_only=True)
    tasks = serializers.SerializerMethodField()
    # Spec 007 D7: Shipper đang giữ hàng đã bị khóa → đơn chờ đổi Shipper (spec 009). Chỉ Nhân viên.
    holder_locked = serializers.SerializerMethodField()
    # Spec 007 D11: kết quả giao thành công (thời gian, COD đã thu) — mọi vai trò xem được đơn.
    delivery = serializers.SerializerMethodField()
    # Spec 008: Shop đã nhận lại hàng hoàn (thời gian, người nhận) — mọi vai trò xem được đơn.
    return_result = serializers.SerializerMethodField()

    STAFF_ONLY_FIELDS = ("holder_shipper", "tasks", "holder_locked")

    class Meta:
        model = Shipment
        # holder_type, delivery_attempts: UC05.7 bước 4 (người giữ hàng, số lần giao) — chỉ đọc.
        fields = ["id", "request_code", "tracking_code", "status", "shop", *CONTENT_FIELDS,
                  "holder_type", "delivery_attempts", "created_at", "updated_at", "allowed_actions",
                  "rejection_reason", "holder_shipper", "tasks", "holder_locked", "delivery", "return_result"]
        read_only_fields = fields

    def get_allowed_actions(self, obj):
        # Bảng trạng thái + điều kiện phụ (vd: hết lượt giao — spec 007 D8).
        return shipment_allowed_actions(obj, self.context["request"].user.role)

    def get_holder_locked(self, obj):
        shipper = obj.holder_shipper  # select_related ở detail_response
        return obj.holder_type == HolderType.SHIPPER and shipper is not None and not shipper.is_active

    def get_return_result(self, obj):
        """Chỉ truy vấn khi Đã hoàn về Shop."""
        if obj.status != ShipmentStatus.RETURNED_TO_SHOP:
            return None
        from apps.dispatch.constants import HandoverKind  # muộn: dispatch import shipments
        from apps.dispatch.models import Handover

        handover = (Handover.objects.filter(shipment=obj, kind=HandoverKind.SHOP_PICKUP)
                    .order_by("-received_at", "-id").first())
        if handover is None:
            return None
        return {"received_at": serializers.DateTimeField().to_representation(handover.received_at),
                "receiver_name": handover.receiver_name}

    def get_delivery(self, obj):
        """Chỉ truy vấn khi đơn Đã giao (giống rejection_reason)."""
        if obj.status != ShipmentStatus.DELIVERED:
            return None
        from apps.dispatch.constants import TaskStatus, TaskType  # muộn: dispatch import shipments
        from apps.dispatch.models import TaskResult

        result = (TaskResult.objects.select_related("task")
                  .filter(task__shipment=obj, task__type=TaskType.DELIVERY, outcome=TaskStatus.SUCCEEDED).first())
        if result is None:
            return None
        return {"delivered_at": serializers.DateTimeField().to_representation(result.recorded_at),
                "cod_collected": result.cod_collected, "attempt_no": result.task.attempt_no}

    def _is_staff(self):
        return self.context["request"].user.role == UserRole.ADMIN

    def get_tasks(self, obj):
        from apps.dispatch.serializers import TaskSummarySerializer  # muộn: dispatch.serializers import file này

        # Queryset của chi tiết cho Nhân viên prefetch sẵn (shipments.views.detail_response) — không N+1.
        return TaskSummarySerializer(obj.tasks.all(), many=True).data

    def to_representation(self, instance):
        if self._is_staff():
            return super().to_representation(instance)
        # Shop: bỏ hẳn trường nội bộ (không chỉ để rỗng) và không chạy truy vấn nhiệm vụ.
        fields = self.fields
        for name in self.STAFF_ONLY_FIELDS:
            fields.pop(name, None)
        return super().to_representation(instance)

    def get_rejection_reason(self, obj):
        if obj.status != ShipmentStatus.REJECTED:
            return None
        return (
            obj.events.filter(action=ShipmentAction.REJECT_REQUEST)
            .order_by("-created_at", "-id")
            .values_list("reason", flat=True)
            .first()
        )


class ShipmentListQuerySerializer(serializers.Serializer):
    status = serializers.ListField(child=serializers.ChoiceField(choices=ShipmentStatus.choices), required=False)
    q = serializers.CharField(required=False, allow_blank=True, max_length=SEARCH_QUERY_MAX_LENGTH)
    # Spec 005 (UC05.9): khoảng ngày tạo, tính theo giờ nghiệp vụ, gồm cả hai đầu.
    created_from = serializers.DateField(required=False)
    created_to = serializers.DateField(required=False)
    ordering = serializers.ChoiceField(choices=list(SHIPMENT_LIST_ORDERINGS), required=False,
                                       default=DEFAULT_SHIPMENT_ORDERING)

    def validate(self, attrs):
        start, end = attrs.get("created_from"), attrs.get("created_to")
        if start and end and start > end:
            raise serializers.ValidationError({"created_to": [DATE_RANGE_INVALID_MESSAGE]})
        return attrs


class ShipmentUpdateSerializer(ShipmentWriteSerializer):
    """Sửa yêu cầu (UC05.1): một phần trường nội dung + `updated_at` đã tải (chống ghi đè)."""

    updated_at = serializers.DateTimeField(write_only=True)

    class Meta(ShipmentWriteSerializer.Meta):
        fields = [*CONTENT_FIELDS, "updated_at"]


class CancelShipmentSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=CANCEL_REASON_MAX_LENGTH, default="")


class ApproveShipmentSerializer(serializers.Serializer):
    """Duyệt (UC05.6): `updated_at` của bản Nhân viên đang xem — Shop vừa sửa thì 409 (spec 005 D2)."""

    updated_at = serializers.DateTimeField(error_messages={"required": MISSING_VERSION_MESSAGE})


class RejectShipmentSerializer(ApproveShipmentSerializer):
    """Từ chối (UC05.8): lý do bắt buộc, cắt khoảng trắng (D5)."""

    reason = serializers.CharField(
        max_length=EVENT_REASON_MAX_LENGTH,
        error_messages={"required": REJECT_REASON_REQUIRED_MESSAGE, "blank": REJECT_REASON_REQUIRED_MESSAGE},
    )


class ShipmentEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    task = serializers.SerializerMethodField()

    def get_actor(self, obj):
        if obj.actor_id is None:
            return None
        request = self.context.get("request")
        if request is not None and request.user.role == UserRole.ADMIN:
            return EventActorSerializer(obj.actor).data
        # Shop chỉ nhận danh tính hiển thị, không username/SĐT nội bộ; không đổi serializer dùng chung accounts.
        return {"id": obj.actor_id, "full_name": obj.actor.full_name}

    def get_task(self, obj):
        task = obj.task
        if task is None:
            return None
        return {"id": task.pk, "type": task.type, "attempt_no": task.attempt_no,
                "pickup_no": self.context.get("pickup_numbers", {}).get(task.pk)}

    class Meta:
        model = ShipmentEvent
        fields = ["id", "action", "from_status", "to_status", "actor", "reason", "changes", "created_at", "task"]
        read_only_fields = fields
