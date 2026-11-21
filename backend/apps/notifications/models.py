"""Thông báo nội bộ theo tài khoản. Không gửi email/SMS."""
from django.conf import settings
from django.db import models
from django.db.models import Q

from .constants import NotificationKind


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="người nhận",
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=False,  # đã có index ghép bắt đầu bằng recipient (xem Meta.indexes)
    )
    kind = models.CharField("loại", max_length=40, choices=NotificationKind.choices)
    title = models.CharField("tiêu đề", max_length=200)
    body = models.TextField("nội dung", blank=True, default="")
    # Liên kết đối tượng nghiệp vụ, vd {"shipment_id": 12}. Không chứa dữ liệu nhạy cảm.
    payload = models.JSONField("dữ liệu liên kết", blank=True, default=dict)
    created_at = models.DateTimeField("tạo lúc", auto_now_add=True)
    read_at = models.DateTimeField("đọc lúc", null=True, blank=True)

    class Meta:
        verbose_name = "thông báo"
        verbose_name_plural = "thông báo"
        ordering = ["-created_at", "-id"]
        # Khớp đúng thứ tự `ordering` để danh sách trang 1 đọc thẳng từ index, không phải sắp xếp.
        indexes = [
            models.Index(fields=["recipient", "-created_at", "-id"], name="notif_recipient_created_idx"),
            # Chỉ chứa thông báo chưa đọc: phục vụ ?unread=true và đếm chưa đọc; nhỏ dần khi người dùng đọc.
            models.Index(
                fields=["recipient", "-created_at", "-id"],
                name="notif_recipient_unread_idx",
                condition=Q(read_at__isnull=True),
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} → {self.recipient_id}"

    @property
    def is_read(self):
        return self.read_at is not None
