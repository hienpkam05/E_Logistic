"""Tạo thông báo nội bộ.

Gọi bên trong transaction của nghiệp vụ để thông báo chỉ tồn tại khi thao tác
nghiệp vụ lưu thành công (đặc tả mục 2: không lặp nghiệp vụ để gửi lại thông báo).
"""
from django.db import transaction

from .constants import NotificationKind
from .models import Notification


def notify(recipients, kind, title, body="", payload=None):
    """Tạo một thông báo cho mỗi người nhận (bỏ trùng, bỏ None). Trả danh sách đã tạo.

    recipients: một User hoặc iterable User.
    Raise RuntimeError nếu gọi ngoài transaction; ValueError nếu kind không hợp lệ.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("notify() phải được gọi bên trong transaction.atomic() của nghiệp vụ.")
    kind = NotificationKind(kind)

    if recipients is None or not hasattr(recipients, "__iter__"):
        recipients = [recipients]
    unique = {user.pk: user for user in recipients if user is not None}

    notifications = [
        Notification(recipient=user, kind=kind, title=title, body=body, payload=dict(payload or {}))
        for user in unique.values()
    ]
    return Notification.objects.bulk_create(notifications)
