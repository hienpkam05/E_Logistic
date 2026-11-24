"""API điều phối (spec 006). Chi tiết: specs/006-lay-hang-diem-tap-ket/api.md."""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.accounts.permissions import HasRole
from apps.core.constants import SEARCH_QUERY_MAX_LENGTH
from apps.shipments.permissions import shipments_visible_to
from apps.shipments.views import detail_response

from . import services
from .constants import OPEN_TASK_STATUSES, SHIPPER_PICKER_LIMIT, TERMINAL_TASK_STATUSES
from .permissions import tasks_visible_to
from .models import Task
from .serializers import (
    AssignDeliverySerializer,
    ConfirmDeliverySerializer,
    FailDeliverySerializer,
    AssignPickupSerializer,
    ConfirmShopReceivedSerializer,
    FailPickupSerializer,
    ReceiveAtHubSerializer,
    ShipperSerializer,
    StaffDecisionSerializer,
    TaskDetailSerializer,
    TaskListQuerySerializer,
    TaskListSerializer,
    SwapShipperSerializer,
    ConfirmSwapHandoverSerializer,
    OpenTaskSerializer,
)

IsStaff = HasRole.of(UserRole.ADMIN)
IsShipper = HasRole.of(UserRole.SHIPPER)


class ShipperPickerView(APIView):
    """Shipper đang hoạt động để chọn khi phân công (UC06.5 bước 2), ít việc trước (D10). Một truy vấn."""

    permission_classes = [IsStaff]

    def get(self, request):
        term = request.query_params.get("q", "").strip()[:SEARCH_QUERY_MAX_LENGTH]
        queryset = (
            User.objects.filter(role=UserRole.SHIPPER, is_active=True)
            .annotate(open_task_count=Count("tasks", filter=Q(tasks__status__in=sorted(OPEN_TASK_STATUSES))))
            .order_by("open_task_count", "full_name", "id")
        )
        if term:
            queryset = queryset.filter(Q(full_name__icontains=term) | Q(username__icontains=term)
                                       | Q(phone__icontains=term))
        return Response(ShipperSerializer(queryset[:SHIPPER_PICKER_LIMIT], many=True).data)


class ShipperOpenTasksView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        shipper = get_object_or_404(User, pk=pk, role=UserRole.SHIPPER)
        tasks = Task.objects.filter(shipper=shipper, status__in=OPEN_TASK_STATUSES).select_related("shipment")
        return Response(OpenTaskSerializer(tasks, many=True).data)


class _StaffShipmentAction(APIView):
    """Khuôn chung: 404 trước lỗi dữ liệu → kiểm dữ liệu → service → trả chi tiết đơn mới."""

    permission_classes = [IsStaff]
    serializer_class = None

    def perform(self, request, pk, data):  # pragma: no cover - lớp con định nghĩa
        raise NotImplementedError

    def post(self, request, pk):
        get_object_or_404(shipments_visible_to(request.user), pk=pk)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform(request, pk, serializer.validated_data)
        return detail_response(request, pk)


class SwapShipperView(_StaffShipmentAction):
    serializer_class = SwapShipperSerializer

    def perform(self, request, pk, data):
        services.swap_shipper(request.user, pk, data["shipper_id"], data["reason"], data["updated_at"])


class ConfirmSwapHandoverView(_StaffShipmentAction):
    serializer_class = ConfirmSwapHandoverSerializer

    def perform(self, request, pk, data):
        services.confirm_swap_handover(request.user, pk, data["discrepancy_note"], data["updated_at"])


class ReportSwapIssueView(_StaffShipmentAction):
    serializer_class = StaffDecisionSerializer

    def perform(self, request, pk, data):
        services.report_swap_issue(request.user, pk, data["reason"], data["updated_at"])


class RecallToHubView(_StaffShipmentAction):
    serializer_class = ReceiveAtHubSerializer

    def perform(self, request, pk, data):
        services.recall_to_hub(request.user, pk, data["discrepancy_note"], data["updated_at"])


class AssignPickupView(_StaffShipmentAction):
    """UC06.5."""

    serializer_class = AssignPickupSerializer

    def perform(self, request, pk, data):
        services.assign_pickup(request.user, pk, data["shipper_id"], data["updated_at"])


class ReceiveAtHubView(_StaffShipmentAction):
    """UC04.10."""

    serializer_class = ReceiveAtHubSerializer

    def perform(self, request, pk, data):
        services.receive_at_hub(request.user, pk, data["discrepancy_note"].strip(), data["updated_at"])


class RetryPickupView(_StaffShipmentAction):
    """UC04.13 — lấy lại."""

    serializer_class = StaffDecisionSerializer

    def perform(self, request, pk, data):
        services.retry_pickup(request.user, pk, data["reason"], data["updated_at"])


class AbandonPickupView(_StaffShipmentAction):
    """UC04.13 A1 — kết thúc do không lấy được hàng."""

    serializer_class = StaffDecisionSerializer

    def perform(self, request, pk, data):
        services.abandon_pickup(request.user, pk, data["reason"], data["updated_at"])


class AssignDeliveryView(_StaffShipmentAction):
    """UC06.6 (spec 007)."""

    serializer_class = AssignDeliverySerializer

    def perform(self, request, pk, data):
        services.assign_delivery(request.user, pk, data["shipper_id"], data["updated_at"])


class DecideRedeliveryView(_StaffShipmentAction):
    """UC04.12 — giao lại."""

    serializer_class = StaffDecisionSerializer

    def perform(self, request, pk, data):
        services.decide_redelivery(request.user, pk, data["reason"], data["updated_at"])


class AssignReturnView(_StaffShipmentAction):
    """UC06.7 (spec 008)."""

    serializer_class = AssignPickupSerializer  # cùng dữ liệu: shipper_id + updated_at

    def perform(self, request, pk, data):
        services.assign_return(request.user, pk, data["shipper_id"], data["updated_at"])


class ReceiveReturnView(_StaffShipmentAction):
    """UC04.9 bước 4–7, UC06.7 A1.2."""

    serializer_class = ReceiveAtHubSerializer  # cùng dữ liệu: ghi chú sai lệch + updated_at

    def perform(self, request, pk, data):
        services.receive_return(request.user, pk, data["discrepancy_note"].strip(), data["updated_at"])


class ReportReturnIssueView(_StaffShipmentAction):
    """UC04.9 E1 — ghi sai lệch, chưa nhận."""

    serializer_class = StaffDecisionSerializer

    def perform(self, request, pk, data):
        services.report_return_issue(request.user, pk, data["reason"], data["updated_at"])


class ConfirmShopReceivedView(_StaffShipmentAction):
    """UC04.11."""

    serializer_class = ConfirmShopReceivedSerializer

    def perform(self, request, pk, data):
        services.confirm_shop_received(request.user, pk, data["receiver_name"].strip(), data["note"].strip(),
                                       data["updated_at"])


class DecideReturnView(_StaffShipmentAction):
    """UC04.12 A1 — chuyển hoàn."""

    serializer_class = StaffDecisionSerializer

    def perform(self, request, pk, data):
        services.decide_return(request.user, pk, data["reason"], data["updated_at"])


# ---------------------------------------------------------------- Phía Shipper

def _task_queryset(user):
    return tasks_visible_to(user).select_related("shipment__shop", "shipment__pickup_ward", "shipment__delivery_ward",
                                                 "result")


class TaskListView(ListAPIView):
    """UC04.1, UC04.4: nhiệm vụ của Shipper đang đăng nhập, mới phân công trước. ?type=PICKUP|DELIVERY&open=true|false."""

    permission_classes = [IsShipper]
    serializer_class = TaskListSerializer

    def get_queryset(self):
        query = TaskListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        queryset = _task_queryset(self.request.user)
        if params.get("type"):
            queryset = queryset.filter(type=params["type"])
        if params["open"] is True:
            queryset = queryset.filter(status__in=sorted(OPEN_TASK_STATUSES))
        elif params["open"] is False:
            queryset = queryset.filter(status__in=sorted(TERMINAL_TASK_STATUSES))
        return queryset.order_by("-assigned_at", "-id")


def _task_response(request, task_id):
    task = get_object_or_404(_task_queryset(request.user), pk=task_id)
    return Response(TaskDetailSerializer(task, context={"request": request}).data)


class TaskDetailView(APIView):
    """Chi tiết nhiệm vụ (UC04.1 bước 5, UC04.4 bước 5). Nhiệm vụ không phải của mình → 404 như không tồn tại."""

    permission_classes = [IsShipper]

    def get(self, request, pk):
        return _task_response(request, pk)


class _ShipperTaskAction(APIView):
    """Khuôn chung: (có dữ liệu) 404 trước lỗi dữ liệu → kiểm dữ liệu → service → trả chi tiết nhiệm vụ mới."""

    permission_classes = [IsShipper]
    serializer_class = None

    def perform(self, request, pk, data):  # pragma: no cover - lớp con định nghĩa
        raise NotImplementedError

    def post(self, request, pk):
        data = {}
        if self.serializer_class is not None:
            get_object_or_404(tasks_visible_to(request.user), pk=pk)
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
        self.perform(request, pk, data)
        return _task_response(request, pk)


class ConfirmPickupView(_ShipperTaskAction):
    """UC04.2."""

    def perform(self, request, pk, data):
        services.confirm_pickup(request.user, pk)


class FailPickupView(_ShipperTaskAction):
    """UC04.3."""

    serializer_class = FailPickupSerializer

    def perform(self, request, pk, data):
        services.fail_pickup(request.user, pk, data["reason_code"], data["note"])


class ConfirmDeliveryView(_ShipperTaskAction):
    """UC04.5 + UC04.7 (spec 007)."""

    serializer_class = ConfirmDeliverySerializer

    def perform(self, request, pk, data):
        services.confirm_delivery(request.user, pk, data["cod_collected"])


class ReportReturnHandoverView(_ShipperTaskAction):
    """UC04.9 bước 1–3 (spec 008)."""

    def perform(self, request, pk, data):
        services.report_return_handover(request.user, pk)


class ReportSwapHandoverView(_ShipperTaskAction):
    """UC06.8 A1.3: người cũ báo đã đưa hàng về, chờ Nhân viên xác nhận."""

    def perform(self, request, pk, data):
        services.report_swap_handover(request.user, pk)


class FailDeliveryView(_ShipperTaskAction):
    """UC04.6 (spec 007)."""

    serializer_class = FailDeliverySerializer

    def perform(self, request, pk, data):
        services.fail_delivery(request.user, pk, data["reason_code"], data["note"])
