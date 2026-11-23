"""Yêu cầu gửi hàng / vận đơn, lịch sử vận chuyển, danh mục phường/xã (spec 004)."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q

from apps.accounts.constants import PHONE_INVALID_MESSAGE, PHONE_REGEX

from .constants import (
    ADDRESS_MAX_LENGTH,
    COD_MAX_VND,
    MAX_DELIVERY_ATTEMPTS,
    DESCRIPTION_MAX_LENGTH,
    EVENT_REASON_MAX_LENGTH,
    INITIAL_SHIPMENT_STATUS,
    NOTE_MAX_LENGTH,
    PACKAGE_COUNT_MAX,
    PACKAGE_COUNT_MIN,
    REQUEST_CODE_DIGITS,
    REQUEST_CODE_PREFIX,
    WEIGHT_GRAMS_MAX,
    HolderType,
    ShipmentAction,
    ShipmentStatus,
)

phone_validator = RegexValidator(PHONE_REGEX, PHONE_INVALID_MESSAGE)
REQUEST_CODE_REGEX = rf"^{REQUEST_CODE_PREFIX}\d{{{REQUEST_CODE_DIGITS}}}$"


class Ward(models.Model):
    """Phường/xã thuộc Hà Nội. Nạp bằng `load_wards`; không xóa — ngừng dùng bằng is_active=False."""

    code = models.CharField("mã", max_length=20, unique=True)
    name = models.CharField("tên", max_length=100)
    is_active = models.BooleanField("đang dùng", default=True)

    class Meta:
        verbose_name = "phường/xã"
        verbose_name_plural = "phường/xã"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Shipment(models.Model):
    """Yêu cầu gửi hàng của Shop; thành vận đơn khi được duyệt (có tracking_code — spec 005)."""

    request_code = models.CharField("mã yêu cầu", max_length=12, unique=True, null=True, blank=True)
    tracking_code = models.CharField("mã vận đơn", max_length=20, unique=True, null=True, blank=True)
    shop = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Shop", on_delete=models.PROTECT, related_name="shipments",
        db_index=False,  # index ghép (shop, -created_at, -id) bên dưới
    )
    status = models.CharField("trạng thái", max_length=30, choices=ShipmentStatus.choices,
                              default=INITIAL_SHIPMENT_STATUS)

    # Bản chụp thông tin tại thời điểm tạo/sửa — sửa hồ sơ Shop không đổi đơn cũ (UC02.2 BR2).
    sender_name = models.CharField("người gửi", max_length=150)
    sender_phone = models.CharField("SĐT người gửi", max_length=10, validators=[phone_validator])
    pickup_ward = models.ForeignKey(Ward, verbose_name="phường/xã lấy hàng", on_delete=models.PROTECT,
                                    related_name="+")
    pickup_address = models.CharField("địa chỉ lấy hàng", max_length=ADDRESS_MAX_LENGTH)
    receiver_name = models.CharField("người nhận", max_length=150)
    receiver_phone = models.CharField("SĐT người nhận", max_length=10, validators=[phone_validator])
    delivery_ward = models.ForeignKey(Ward, verbose_name="phường/xã giao hàng", on_delete=models.PROTECT,
                                      related_name="+")
    delivery_address = models.CharField("địa chỉ giao hàng", max_length=ADDRESS_MAX_LENGTH)

    package_description = models.CharField("mô tả kiện hàng", max_length=DESCRIPTION_MAX_LENGTH)
    package_count = models.PositiveSmallIntegerField(
        "số kiện", default=PACKAGE_COUNT_MIN,
        validators=[MinValueValidator(PACKAGE_COUNT_MIN), MaxValueValidator(PACKAGE_COUNT_MAX)],
    )
    weight_grams = models.PositiveIntegerField(
        "khối lượng (gram)", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(WEIGHT_GRAMS_MAX)],
    )
    cod_amount = models.PositiveBigIntegerField("COD (VND)", default=0, validators=[MaxValueValidator(COD_MAX_VND)])
    note = models.CharField("ghi chú", max_length=NOTE_MAX_LENGTH, blank=True, default="")

    # Dùng từ spec 006–007.
    holder_type = models.CharField("đang giữ hàng", max_length=20, choices=HolderType.choices,
                                   default=HolderType.SHOP)
    holder_shipper = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Shipper đang giữ hàng", on_delete=models.PROTECT,
        null=True, blank=True, related_name="held_shipments",
    )
    delivery_attempts = models.PositiveSmallIntegerField("số lần đã giao", default=0)

    created_at = models.DateTimeField("tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("cập nhật lúc", auto_now=True)

    class Meta:
        verbose_name = "vận đơn"
        verbose_name_plural = "vận đơn"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["shop", "-created_at", "-id"], name="ship_shop_created_idx"),
            # Spec 005 (EXPLAIN 30.000 đơn): Nhân viên xem toàn hệ thống, không lọc shop → cần index theo thời gian;
            # thêm -id để khớp thứ tự (created_at, id), khỏi bước Sort. Quét ngược phục vụ cả chiều tăng dần.
            models.Index(fields=["-created_at", "-id"], name="ship_created_idx"),
            models.Index(fields=["status", "-created_at", "-id"], name="ship_status_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(status__in=ShipmentStatus.values), name="ship_status_valid"),
            models.CheckConstraint(condition=Q(holder_type__in=HolderType.values), name="ship_holder_type_valid"),
            models.CheckConstraint(
                condition=Q(package_count__gte=PACKAGE_COUNT_MIN, package_count__lte=PACKAGE_COUNT_MAX),
                name="ship_package_count_range",
            ),
            models.CheckConstraint(
                condition=Q(weight_grams__isnull=True) | Q(weight_grams__gte=1, weight_grams__lte=WEIGHT_GRAMS_MAX),
                name="ship_weight_range",
            ),
            models.CheckConstraint(condition=Q(cod_amount__lte=COD_MAX_VND), name="ship_cod_max"),
            # Spec 007 D8: tối đa 3 lần giao thực tế (cột PositiveSmallInteger đã chặn âm).
            models.CheckConstraint(condition=Q(delivery_attempts__lte=MAX_DELIVERY_ATTEMPTS),
                                   name="ship_delivery_attempts_max"),
            models.CheckConstraint(
                condition=Q(sender_phone__regex=PHONE_REGEX) & Q(receiver_phone__regex=PHONE_REGEX),
                name="ship_phones_format",
            ),
            models.CheckConstraint(
                condition=Q(request_code__isnull=True) | Q(request_code__regex=REQUEST_CODE_REGEX),
                name="ship_request_code_format",
            ),
        ]

    def __str__(self):
        return self.tracking_code or self.request_code or f"#{self.pk}"

    @property
    def display_code(self):
        """Mã hiển thị: mã vận đơn nếu đã duyệt, ngược lại mã yêu cầu (UC05.3 BR2)."""
        return self.tracking_code or self.request_code

    @staticmethod
    def build_request_code(pk):
        return f"{REQUEST_CODE_PREFIX}{pk:0{REQUEST_CODE_DIGITS}d}"


class ShipmentEvent(models.Model):
    """Lịch sử vận chuyển — chỉ thêm, không sửa/xóa (UC03.2 BR1)."""

    shipment = models.ForeignKey(
        Shipment, verbose_name="vận đơn", on_delete=models.PROTECT, related_name="events",
        db_index=False,  # index ghép (shipment, -created_at, -id) bên dưới
    )
    action = models.CharField("hành động", max_length=30, choices=ShipmentAction.choices)
    from_status = models.CharField("trạng thái trước", max_length=30, choices=ShipmentStatus.choices,
                                   null=True, blank=True)
    to_status = models.CharField("trạng thái sau", max_length=30, choices=ShipmentStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người thực hiện", on_delete=models.PROTECT,
        null=True, blank=True, related_name="shipment_events",
    )
    reason = models.CharField("lý do", max_length=EVENT_REASON_MAX_LENGTH, blank=True, default="")
    changes = models.JSONField("thay đổi", blank=True, default=dict)
    # Spec 006: mốc gắn với nhiệm vụ nào (phân công, lấy, giao…). Chuỗi "app.Model" tránh import vòng.
    task = models.ForeignKey(
        "dispatch.Task", verbose_name="nhiệm vụ", on_delete=models.PROTECT, null=True, blank=True,
        related_name="events", db_index=False,  # không truy vấn lịch sử theo nhiệm vụ; xem theo đơn
    )
    created_at = models.DateTimeField("lúc", auto_now_add=True)

    class Meta:
        verbose_name = "lịch sử vận đơn"
        verbose_name_plural = "lịch sử vận đơn"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["shipment", "-created_at", "-id"], name="ship_event_shipment_idx")]

    def __str__(self):
        return f"{self.get_action_display()} · {self.shipment_id}"
