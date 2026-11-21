from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "payload", "created_at", "read_at", "is_read"]
        read_only_fields = fields


class NotificationListQuerySerializer(serializers.Serializer):
    """Tham số lọc danh sách: ?unread=true chỉ lấy chưa đọc."""

    unread = serializers.BooleanField(required=False, default=None, allow_null=True)
