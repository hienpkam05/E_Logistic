"""Serializer điều phối (spec 006). Không import apps.shipments.serializers ở mức module (shipments import file này)."""
from typing import NamedTuple

from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import EventActorSerializer

from apps.shipments.constants import COD_MAX_VND, ShipmentAction
from apps.shipments.rules import shipment_allowed_actions

from .constants import (
    FAIL_NOTE_REQUIRED_MESSAGE,
    HANDOVER_REQUIRED_MESSAGE,
    RECEIVER_NAME_MAX_LENGTH,
    RECEIVER_NAME_REQUIRED_MESSAGE,
    VERIFIED_REQUIRED_MESSAGE,
    DeliveryFailReason,
    HANDOVER_NOTE_MAX_LENGTH,
    REASON_REQUIRED_MESSAGE,
    RESULT_NOTE_MAX_LENGTH,
    PickupFailReason,
    TaskStatus,
    TaskType,
)

from .models import Task, TaskResult


class ShipperSerializer(EventActorSerializer):
    """Một người để chọn khi phân công (+ số nhiệm vụ đang mở để chia việc — D10)."""

    open_task_count = serializers.IntegerField(read_only=True)

    class Meta(EventActorSerializer.Meta):
        model = User
        fields = [*EventActorSerializer.Meta.fields, "phone", "open_task_count"]
        read_only_fields = fields


class PersonSerializer(EventActorSerializer):
    class Meta(EventActorSerializer.Meta):
        fields = [*EventActorSerializer.Meta.fields, "phone"]
        read_only_fields = fields


class TaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResult
        fields = ["outcome", "reason_code", "note", "cod_expected", "cod_collected", "recorded_at"]
        read_only_fields = fields


class TaskSummarySerializer(serializers.ModelSerializer):
    """Lịch sử nhiệm vụ phía NV; prefetch shipper, assigned_by, result, swap_candidate, replaced_by__shipper."""

    shipper = PersonSerializer(read_only=True)
    assigned_by = EventActorSerializer(read_only=True)
    result = serializers.SerializerMethodField()
    swap_candidate = EventActorSerializer(read_only=True)
    replaced_by = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "type", "status", "attempt_no", "shipper", "assigned_by", "assigned_at", "closed_at",
                  "needs_attention", "handover_reported_at", "result", "swap_candidate", "replaced_by"]
        read_only_fields = fields

    def get_result(self, obj):
        result = getattr(obj, "result", None)  # OneToOne ngược: thiếu thì RelatedObjectDoesNotExist → None
        return TaskResultSerializer(result).data if result else None

    def get_replaced_by(self, obj):
        task = obj.replaced_by
        return {"id": task.pk, "shipper": EventActorSerializer(task.shipper).data} if task else None


# ---- Thao tác Nhân viên trên đơn: cùng khuôn ApproveShipmentSerializer (updated_at bắt buộc) ----

def _versioned():
    from apps.shipments.serializers import ApproveShipmentSerializer  # muộn: tránh vòng import serializers

    return ApproveShipmentSerializer


class AssignPickupSerializer(_versioned()):
    shipper_id = serializers.IntegerField(min_value=1)


class ReceiveAtHubSerializer(_versioned()):
    discrepancy_note = serializers.CharField(max_length=HANDOVER_NOTE_MAX_LENGTH, required=False, allow_blank=True,
                                             default="")


class HandedOverConfirmationSerializer(serializers.Serializer):
    """Xác nhận Shipper đã nhận hàng: dùng cho phân công giao và bàn giao đổi người."""

    handed_over = serializers.BooleanField(error_messages={"required": HANDOVER_REQUIRED_MESSAGE})

    def validate_handed_over(self, value):
        if not value:
            raise serializers.ValidationError(HANDOVER_REQUIRED_MESSAGE)
        return value


class AssignDeliverySerializer(AssignPickupSerializer, HandedOverConfirmationSerializer):
    """UC06.6 bước 3–4 (D6)."""


class ConfirmShopReceivedSerializer(_versioned()):
    """UC04.11 (D7): tên người nhận phía Shop + xác nhận đã kiểm tra người nhận thuộc Shop / được ủy quyền."""

    receiver_name = serializers.CharField(
        max_length=RECEIVER_NAME_MAX_LENGTH,
        error_messages={"required": RECEIVER_NAME_REQUIRED_MESSAGE, "blank": RECEIVER_NAME_REQUIRED_MESSAGE},
    )
    verified = serializers.BooleanField(error_messages={"required": VERIFIED_REQUIRED_MESSAGE})
    note = serializers.CharField(max_length=HANDOVER_NOTE_MAX_LENGTH, required=False, allow_blank=True, default="")

    def validate_verified(self, value):
        if not value:
            raise serializers.ValidationError(VERIFIED_REQUIRED_MESSAGE)
        return value


class StaffDecisionSerializer(_versioned()):
    """Quyết định có lý do (UC04.13 lấy lại / kết thúc, UC04.12 giao lại / hoàn): bắt buộc, cắt khoảng trắng."""

    reason = serializers.CharField(
        max_length=RESULT_NOTE_MAX_LENGTH,
        error_messages={"required": REASON_REQUIRED_MESSAGE, "blank": REASON_REQUIRED_MESSAGE},
    )


class SwapShipperSerializer(StaffDecisionSerializer):
    shipper_id = serializers.IntegerField(min_value=1)


class ConfirmSwapHandoverSerializer(ReceiveAtHubSerializer, HandedOverConfirmationSerializer):
    """UC06.8 A1.4: người dự kiến đã nhận hàng tại điểm tập kết."""


class OpenTaskSerializer(serializers.ModelSerializer):
    shipment = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "type", "status", "needs_attention", "shipment"]
        read_only_fields = fields

    def get_shipment(self, obj):
        return {"id": obj.shipment_id, "tracking_code": obj.shipment.tracking_code, "status": obj.shipment.status}


# ---- Phía Shipper. Quyền tối thiểu: mỗi loại nhiệm vụ chỉ chứa thông tin cần để làm việc đó (spec 006 D3, 007 D3).
# Queryset: select_related shipment__shop, shipment__pickup_ward, shipment__delivery_ward.

def _ward(ward):
    return {"code": ward.code, "name": ward.name}


class PickupShipmentBriefSerializer(serializers.Serializer):
    """Nhiệm vụ LẤY: không người nhận / địa chỉ giao / COD."""

    id = serializers.IntegerField()
    tracking_code = serializers.CharField()
    status = serializers.CharField()
    shop_name = serializers.CharField(source="shop.full_name")
    sender_name = serializers.CharField()
    sender_phone = serializers.CharField()
    pickup_ward = serializers.SerializerMethodField()
    pickup_address = serializers.CharField()
    package_count = serializers.IntegerField()

    def get_pickup_ward(self, obj):
        return _ward(obj.pickup_ward)


class PickupShipmentDetailSerializer(PickupShipmentBriefSerializer):
    package_description = serializers.CharField()
    weight_grams = serializers.IntegerField(allow_null=True)
    note = serializers.CharField()


class DeliveryShipmentBriefSerializer(serializers.Serializer):
    """Nhiệm vụ GIAO (UC04.4 bước 3): người nhận, địa chỉ giao, COD. Không SĐT người gửi / địa chỉ lấy."""

    id = serializers.IntegerField()
    tracking_code = serializers.CharField()
    status = serializers.CharField()
    shop_name = serializers.CharField(source="shop.full_name")
    receiver_name = serializers.CharField()
    receiver_phone = serializers.CharField()
    delivery_ward = serializers.SerializerMethodField()
    delivery_address = serializers.CharField()
    package_count = serializers.IntegerField()
    cod_amount = serializers.IntegerField()

    def get_delivery_ward(self, obj):
        return _ward(obj.delivery_ward)


class DeliveryShipmentDetailSerializer(DeliveryShipmentBriefSerializer):
    package_description = serializers.CharField()
    weight_grams = serializers.IntegerField(allow_null=True)
    note = serializers.CharField()


class ReturnShipmentBriefSerializer(serializers.Serializer):
    """Nhiệm vụ HOÀN (UC04.8 bước 3, spec 008 D8): mã đơn + tình trạng hàng. Không người nhận / COD / SĐT người gửi.

    Điểm tập kết lấy từ /meta/choices/ `hub` (một nguồn), không lặp trong từng nhiệm vụ.
    """

    id = serializers.IntegerField()
    tracking_code = serializers.CharField()
    status = serializers.CharField()
    shop_name = serializers.CharField(source="shop.full_name")
    package_description = serializers.CharField()
    package_count = serializers.IntegerField()


class ReturnShipmentDetailSerializer(ReturnShipmentBriefSerializer):
    weight_grams = serializers.IntegerField(allow_null=True)
    note = serializers.CharField()
    return_reason = serializers.SerializerMethodField()

    def get_return_reason(self, obj):
        """Lý do quyết định hoàn (UC04.12) — chỉ ở chi tiết (một truy vấn), danh sách không cần."""
        return (obj.events.filter(action=ShipmentAction.DECIDE_RETURN).order_by("-created_at", "-id")
                .values_list("reason", flat=True).first())


class ShipmentView(NamedTuple):
    brief: type
    detail: type
    # SĐT liên hệ — ẩn khi nhiệm vụ đã đóng (UC04.4 BR2, spec 007 D3). None: loại nhiệm vụ không có SĐT liên hệ.
    contact_field: str | None


# Loại nhiệm vụ → cách hiển thị đơn cho Shipper. Spec 008 thêm RETURN.
TASK_SHIPMENT_VIEWS = {
    TaskType.PICKUP: ShipmentView(PickupShipmentBriefSerializer, PickupShipmentDetailSerializer, "sender_phone"),
    TaskType.DELIVERY: ShipmentView(DeliveryShipmentBriefSerializer, DeliveryShipmentDetailSerializer,
                                    "receiver_phone"),
    TaskType.RETURN: ShipmentView(ReturnShipmentBriefSerializer, ReturnShipmentDetailSerializer, None),  # spec 008
}

# Hành động một lần trên nhiệm vụ: đã làm (trường có giá trị) thì bỏ khỏi allowed_actions dù trạng thái đơn còn cho.
TASK_ONE_TIME_ACTIONS = {
    ShipmentAction.REPORT_RETURN_HANDOVER: "handover_reported_at",  # spec 008 D4
    ShipmentAction.REPORT_SWAP_HANDOVER: "handover_reported_at",  # spec 009 D4
}

# Hành động của Shipper chỉ hợp lệ ở một trạng thái NHIỆM VỤ (spec 009 D4): đang chờ bàn giao đổi người thì người cũ
# mất giao / thất bại / COD, chỉ còn báo đã đưa về. Service đã chặn (qua TASK_TRANSITIONS) — bảng này để nút khớp.
TASK_STATUS_FOR_ACTION = {
    ShipmentAction.CONFIRM_PICKUP: TaskStatus.ACTIVE,
    ShipmentAction.FAIL_PICKUP: TaskStatus.ACTIVE,
    ShipmentAction.CONFIRM_DELIVERY: TaskStatus.ACTIVE,
    ShipmentAction.FAIL_DELIVERY: TaskStatus.ACTIVE,
    ShipmentAction.REPORT_RETURN_HANDOVER: TaskStatus.ACTIVE,
    ShipmentAction.REPORT_SWAP_HANDOVER: TaskStatus.PENDING_SWAP_HANDOVER,
}


class TaskListSerializer(serializers.ModelSerializer):
    shipment = serializers.SerializerMethodField()
    shipment_view = "brief"

    class Meta:
        model = Task
        fields = ["id", "type", "status", "attempt_no", "assigned_at", "closed_at", "needs_attention",
                  "handover_reported_at", "shipment"]
        read_only_fields = fields

    def get_shipment(self, obj):
        view = TASK_SHIPMENT_VIEWS[obj.type]
        data = getattr(view, self.shipment_view)(obj.shipment).data
        if not obj.is_open and view.contact_field:
            data[view.contact_field] = None
        return data


class TaskDetailSerializer(TaskListSerializer):
    shipment_view = "detail"
    allowed_actions = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    class Meta(TaskListSerializer.Meta):
        fields = [*TaskListSerializer.Meta.fields, "allowed_actions", "result"]
        read_only_fields = fields

    def get_allowed_actions(self, obj):
        """Từ bảng trạng thái (không if/else): nhiệm vụ còn mở → hành động vận đơn Shipper được làm ở trạng thái đơn."""
        if not obj.is_open:
            return []
        actions = shipment_allowed_actions(obj.shipment, self.context["request"].user.role)
        return [a for a in actions
                if not getattr(obj, TASK_ONE_TIME_ACTIONS.get(a, ""), None)
                and TASK_STATUS_FOR_ACTION.get(a, obj.status) == obj.status]

    def get_result(self, obj):
        result = getattr(obj, "result", None)
        return TaskResultSerializer(result).data if result else None


class TaskListQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=TaskType.choices, required=False)  # bỏ trống = mọi loại (spec 007)
    open = serializers.BooleanField(allow_null=True, default=None)  # None = mọi nhiệm vụ


class FailPickupSerializer(serializers.Serializer):
    """UC04.3: lý do chọn từ danh mục (D4); Khác → ghi chú bắt buộc."""

    REASONS = PickupFailReason
    reason_code = serializers.ChoiceField(choices=PickupFailReason.choices)
    note = serializers.CharField(max_length=RESULT_NOTE_MAX_LENGTH, allow_blank=True, default="")

    def validate(self, attrs):
        attrs["note"] = attrs.get("note", "").strip()
        if attrs["reason_code"] == self.REASONS.OTHER and not attrs["note"]:
            raise serializers.ValidationError({"note": [FAIL_NOTE_REQUIRED_MESSAGE]})
        return attrs


class FailDeliverySerializer(FailPickupSerializer):
    """UC04.6 bước 2–3: lý do giao thất bại (spec 007 D4) — gửi mã lý do lấy hàng → 400."""

    REASONS = DeliveryFailReason
    reason_code = serializers.ChoiceField(choices=DeliveryFailReason.choices)


class ConfirmDeliverySerializer(serializers.Serializer):
    """UC04.7 bước 3–4: số nguyên VND, không âm; đơn không COD gửi 0. So với phải thu ở service (cần khóa đơn)."""

    cod_collected = serializers.IntegerField(min_value=0, max_value=COD_MAX_VND)
