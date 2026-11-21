"""API thông báo nội bộ của chính người đang đăng nhập (spec 002). Chi tiết: specs/002-xac-thuc/api.md."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationListQuerySerializer, NotificationSerializer


def own_notifications(request):
    """Mọi truy vấn đi qua đây: chỉ thông báo của người đang đăng nhập."""
    return Notification.objects.filter(recipient=request.user)


class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        query = NotificationListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        queryset = own_notifications(self.request)
        if query.validated_data["unread"] is True:
            queryset = queryset.filter(read_at__isnull=True)
        elif query.validated_data["unread"] is False:
            queryset = queryset.filter(read_at__isnull=False)
        return queryset  # thứ tự mặc định: mới nhất trước (Meta.ordering)


class UnreadCountView(APIView):
    def get(self, request):
        return Response({"count": own_notifications(request).filter(read_at__isnull=True).count()})


class MarkReadView(APIView):
    def post(self, request, pk):
        notification = get_object_or_404(own_notifications(request), pk=pk)
        # Chỉ ghi lần đầu; gọi lại hoặc hai tab cùng bấm không đổi read_at.
        own_notifications(request).filter(pk=pk, read_at__isnull=True).update(read_at=timezone.now())
        notification.refresh_from_db(fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


class MarkAllReadView(APIView):
    def post(self, request):
        updated = own_notifications(request).filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated})
