"""API yêu cầu gửi hàng / vận đơn (spec 004, 005). Chi tiết: specs/004-yeu-cau-gui-hang/api.md, specs/005-duyet-van-don/api.md."""
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.constants import UserRole
from apps.accounts.permissions import HasRole

from . import services
from .constants import MISSING_VERSION_MESSAGE, SHIPMENT_LIST_ORDERINGS
from .models import ShipmentEvent, Ward
from .permissions import shipments_visible_to
from .serializers import (
    ApproveShipmentSerializer,
    CancelShipmentSerializer,
    RejectShipmentSerializer,
    ShipmentDetailSerializer,
    ShipmentEventSerializer,
    ShipmentListQuerySerializer,
    ShipmentSummarySerializer,
    ShipmentUpdateSerializer,
    ShipmentWriteSerializer,
    WardSerializer,
)

IsShop = HasRole.of(UserRole.SHOP)
IsStaff = HasRole.of(UserRole.ADMIN)
# Đọc danh sách/chi tiết/lịch sử: Shop (đơn của mình) và Nhân viên (toàn hệ thống — spec 005).
CanViewShipments = HasRole.of(UserRole.SHOP, UserRole.ADMIN)


class ShopOnlyForWrites(BasePermission):
    """Ghi (tạo/sửa) chỉ Shop; Nhân viên chỉ đọc qua cùng view (spec 005 D1). Dùng sau CanViewShipments."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.role == UserRole.SHOP


def _start_of_day(day):
    """00:00 của `day` theo giờ nghiệp vụ (TIME_ZONE), dạng có múi giờ để so với created_at."""
    return timezone.make_aware(datetime.combine(day, time.min), timezone.get_default_timezone())


class WardListView(ListAPIView):
    """Phường/xã đang dùng cho form địa chỉ. Mọi vai trò đã đăng nhập; không phân trang (vài trăm dòng)."""

    serializer_class = WardSerializer
    pagination_class = None
    queryset = Ward.objects.filter(is_active=True).order_by("name")


class ShipmentCollectionView(ListAPIView):
    """GET: danh sách (Shop: UC05.3; Nhân viên: UC05.9). POST: tạo yêu cầu (UC05.2, chỉ Shop)."""

    permission_classes = [CanViewShipments, ShopOnlyForWrites]
    serializer_class = ShipmentSummarySerializer

    def get_queryset(self):
        query = ShipmentListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        queryset = shipments_visible_to(self.request.user).select_related("shop", "delivery_ward")
        if params.get("status"):
            queryset = queryset.filter(status__in=params["status"])
        if params.get("created_from"):
            queryset = queryset.filter(created_at__gte=_start_of_day(params["created_from"]))
        if params.get("created_to"):
            queryset = queryset.filter(created_at__lt=_start_of_day(params["created_to"] + timedelta(days=1)))
        term = params.get("q", "").strip()
        if term:
            condition = (
                Q(request_code__icontains=term) | Q(tracking_code__icontains=term)
                | Q(receiver_name__icontains=term) | Q(receiver_phone__icontains=term)
            )
            if self.request.user.role == UserRole.ADMIN:  # Nhân viên tìm thêm theo Shop (spec 005 D7)
                condition |= (
                    Q(shop__full_name__icontains=term) | Q(shop__username__icontains=term)
                    | Q(shop__phone__icontains=term)
                )
            queryset = queryset.filter(condition)
        return queryset.order_by(*SHIPMENT_LIST_ORDERINGS[params["ordering"]])

    def post(self, request):
        serializer = ShipmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shipment = services.create_request(request.user, serializer.validated_data)
        data = ShipmentDetailSerializer(shipment, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)


class ShipmentDetailView(APIView):
    """GET: chi tiết (Shop: UC05.4; Nhân viên: UC05.7). PATCH: sửa yêu cầu (UC05.1, chỉ Shop).

    Đơn ngoài quyền xem → 404 như không tồn tại (BR1).
    """

    permission_classes = [CanViewShipments, ShopOnlyForWrites]

    def get(self, request, pk):
        return detail_response(request, pk)

    def patch(self, request, pk):
        get_object_or_404(shipments_visible_to(request.user), pk=pk)  # 404 trước lỗi dữ liệu
        serializer = ShipmentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "updated_at" not in data:
            raise ValidationError({"updated_at": [MISSING_VERSION_MESSAGE]})
        expected = data.pop("updated_at")
        services.update_request(request.user, pk, data, expected)
        return detail_response(request, pk)


class ShipmentCancelView(APIView):
    """Hủy yêu cầu (UC05.5)."""

    permission_classes = [IsShop]

    def post(self, request, pk):
        serializer = CancelShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_request(request.user, pk, serializer.validated_data["reason"].strip())
        return detail_response(request, pk)


class ShipmentApproveView(APIView):
    """Duyệt yêu cầu (UC05.6) — Nhân viên. Gửi lại khi đã duyệt → 200 trạng thái hiện tại, cùng mã."""

    permission_classes = [IsStaff]

    def post(self, request, pk):
        get_object_or_404(shipments_visible_to(request.user), pk=pk)  # 404 trước lỗi dữ liệu
        serializer = ApproveShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.approve_request(request.user, pk, serializer.validated_data["updated_at"])
        return detail_response(request, pk)


class ShipmentRejectView(APIView):
    """Từ chối yêu cầu (UC05.8) — Nhân viên, lý do bắt buộc."""

    permission_classes = [IsStaff]

    def post(self, request, pk):
        get_object_or_404(shipments_visible_to(request.user), pk=pk)
        serializer = RejectShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.reject_request(request.user, pk, data["reason"], data["updated_at"])
        return detail_response(request, pk)


class ShipmentEventListView(ListAPIView):
    """Lịch sử vận chuyển của một đơn, mới nhất trước (UC05.4, UC05.7, UC03.2). Chỉ đọc."""

    permission_classes = [CanViewShipments]
    serializer_class = ShipmentEventSerializer

    def get_queryset(self):
        shipment = get_object_or_404(shipments_visible_to(self.request.user), pk=self.kwargs["pk"])
        return ShipmentEvent.objects.filter(shipment=shipment).select_related("actor")


def detail_response(request, pk):
    """Chi tiết sau mọi thao tác (dùng chung với dispatch). Nhân viên nhận thêm lịch sử nhiệm vụ (spec 006)."""
    queryset = shipments_visible_to(request.user).select_related("shop", "pickup_ward", "delivery_ward")
    if request.user.role == UserRole.ADMIN:
        from django.db.models import Prefetch

        from apps.dispatch.models import Task

        queryset = queryset.select_related("holder_shipper").prefetch_related(
            Prefetch("tasks", queryset=Task.objects.select_related("shipper", "assigned_by", "result")))
    return Response(ShipmentDetailSerializer(get_object_or_404(queryset, pk=pk), context={"request": request}).data)
