"""Nhiệm vụ lấy / giao / hoàn của Shipper, kết quả nhiệm vụ, bàn giao hàng (spec 006; thiết kế: spec 001 mục 6).

Đổi trạng thái chỉ qua dispatch/services.py (bảng TASK_TRANSITIONS + SHIPMENT_TRANSITIONS), không sửa tay.
Ràng buộc DB là lớp chặn cuối cho các quy tắc "không trùng" (spec 001 mục 3.6 điểm 4).
"""
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.shipments.models import Shipment

from .constants import (
    HANDOVER_NOTE_MAX_LENGTH,
    INITIAL_TASK_STATUS,
    MAX_DELIVERY_ATTEMPTS,
    OPEN_TASK_STATUSES,
    RECEIVER_NAME_MAX_LENGTH,
    RESULT_NOTE_MAX_LENGTH,
    TASK_OUTCOMES,
    TASK_RESULT_REASON_CHOICES,
    TERMINAL_TASK_STATUSES,
    HandoverKind,
    TaskStatus,
    TaskType,
)


class Task(models.Model):
    """Một nhiệm vụ của một Shipper trên một vận đơn. Mỗi đơn tối đa một nhiệm vụ đang mở (D1)."""

    shipment = models.ForeignKey(
        Shipment, verbose_name="vận đơn", on_delete=models.PROTECT, related_name="tasks",
        db_index=False,  # index ghép (shipment, -assigned_at) bên dưới
    )
    type = models.CharField("loại", max_length=20, choices=TaskType.choices)
    status = models.CharField("trạng thái", max_length=30, choices=TaskStatus.choices, default=INITIAL_TASK_STATUS)
    shipper = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Shipper", on_delete=models.PROTECT, related_name="tasks",
        db_index=False,  # index ghép (shipper, -assigned_at, -id) bên dưới
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người phân công", on_delete=models.PROTECT,
        related_name="assigned_tasks", db_index=False,  # không truy vấn theo cột này
    )
    assigned_at = models.DateTimeField("phân công lúc", default=timezone.now)
    closed_at = models.DateTimeField("đóng lúc", null=True, blank=True)
    # Dùng từ spec 007–009.
    replaced_by = models.ForeignKey(
        "self", verbose_name="thay bằng", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", db_index=False,
    )
    handover_reported_at = models.DateTimeField("Shipper báo đã bàn giao lúc", null=True, blank=True)
    # Spec 009 (UC06.8 A1.2): người mới DỰ KIẾN khi Chờ bàn giao đổi Shipper — chưa có quyền nhiệm vụ.
    swap_candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Shipper dự kiến", on_delete=models.PROTECT, null=True, blank=True,
        related_name="+", db_index=False,
    )
    needs_attention = models.BooleanField("cần Nhân viên xử lý", default=False)  # D9: Shipper bị khóa
    attempt_no = models.PositiveSmallIntegerField("lần giao thứ", null=True, blank=True)  # chỉ DELIVERY
    created_at = models.DateTimeField("tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("cập nhật lúc", auto_now=True)

    class Meta:
        verbose_name = "nhiệm vụ"
        verbose_name_plural = "nhiệm vụ"
        ordering = ["-assigned_at", "-id"]
        indexes = [
            models.Index(fields=["shipper", "-assigned_at", "-id"], name="task_shipper_assigned_idx"),
            models.Index(fields=["shipment", "-assigned_at"], name="task_shipment_assigned_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["shipment"], condition=Q(status__in=sorted(OPEN_TASK_STATUSES)),
                name="task_one_open_per_shipment",
            ),
            models.CheckConstraint(condition=Q(type__in=TaskType.values), name="task_type_valid"),
            models.CheckConstraint(condition=Q(status__in=TaskStatus.values), name="task_status_valid"),
            # Đã kết thúc ⇔ có thời điểm đóng.
            models.CheckConstraint(
                condition=(Q(status__in=sorted(TERMINAL_TASK_STATUSES)) & Q(closed_at__isnull=False))
                | (~Q(status__in=sorted(TERMINAL_TASK_STATUSES)) & Q(closed_at__isnull=True)),
                name="task_closed_at_matches_status",
            ),
            # Spec 007: nhiệm vụ GIAO luôn mang số thứ tự lần giao 1..3 (ghi lúc phân công); loại khác không có.
            models.CheckConstraint(
                # isnull=False bắt buộc: so sánh với NULL ra NULL, mà CHECK chỉ chặn khi FALSE (test đã bắt).
                condition=(Q(type=TaskType.DELIVERY)
                           & Q(attempt_no__isnull=False, attempt_no__gte=1, attempt_no__lte=MAX_DELIVERY_ATTEMPTS))
                | (~Q(type=TaskType.DELIVERY) & Q(attempt_no__isnull=True)),
                name="task_attempt_matches_type",
            ),
            # Spec 009: người dự kiến có ⇔ đang Chờ bàn giao đổi Shipper (isnull tường minh — bài học spec 007).
            models.CheckConstraint(
                condition=(Q(status=TaskStatus.PENDING_SWAP_HANDOVER) & Q(swap_candidate__isnull=False))
                | (~Q(status=TaskStatus.PENDING_SWAP_HANDOVER) & Q(swap_candidate__isnull=True)),
                name="task_swap_candidate_only_pending",
            ),
        ]

    def __str__(self):
        return f"{self.get_type_display()} · {self.shipment_id} · {self.get_status_display()}"

    @property
    def is_open(self):
        return self.status in OPEN_TASK_STATUSES


class TaskResult(models.Model):
    """Kết quả cuối do người phụ trách ghi. Một-một với Task: DB chặn ghi kết quả lần hai."""

    task = models.OneToOneField(Task, verbose_name="nhiệm vụ", on_delete=models.PROTECT, related_name="result")
    outcome = models.CharField("kết quả", max_length=20, choices=[(s.value, s.label) for s in TASK_OUTCOMES])
    # Nhóm lý do hợp lệ phụ thuộc task.type (FAIL_REASONS_BY_TASK_TYPE) — kiểm ở serializer; CHECK DB không
    # tham chiếu được bảng Task.
    reason_code = models.CharField("lý do", max_length=40, choices=TASK_RESULT_REASON_CHOICES, null=True,
                                   blank=True)
    note = models.CharField("ghi chú", max_length=RESULT_NOTE_MAX_LENGTH, blank=True, default="")
    # Spec 007 (UC04.5, 04.7): chỉ có ở nhiệm vụ GIAO thành công; đơn không COD → 0 / 0.
    cod_expected = models.PositiveBigIntegerField("COD phải thu (VND)", null=True, blank=True)
    cod_collected = models.PositiveBigIntegerField("COD thực thu (VND)", null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người ghi", on_delete=models.PROTECT, related_name="+",
        db_index=False,
    )
    recorded_at = models.DateTimeField("ghi lúc", default=timezone.now)

    class Meta:
        verbose_name = "kết quả nhiệm vụ"
        verbose_name_plural = "kết quả nhiệm vụ"
        constraints = [
            # Thất bại bắt buộc có lý do; thành công không có lý do. Ràng buộc này cũng chỉ cho phép đúng 2 giá trị
            # outcome (không cần CHECK riêng cho outcome — đột biến spec 006 Phase 1 cho thấy CHECK đó thừa).
            models.CheckConstraint(
                condition=(Q(outcome=TaskStatus.FAILED) & Q(reason_code__isnull=False))
                | (Q(outcome=TaskStatus.SUCCEEDED) & Q(reason_code__isnull=True)),
                name="taskresult_reason_matches_outcome",
            ),
            # Spec 007 D1: hai cột COD cùng có hoặc cùng trống.
            models.CheckConstraint(
                condition=Q(cod_expected__isnull=True, cod_collected__isnull=True)
                | Q(cod_expected__isnull=False, cod_collected__isnull=False),
                name="taskresult_cod_pair",
            ),
            # Có COD thì chỉ ở kết quả thành công và thực thu = phải thu — không thu một phần (UC04.7 BR1).
            models.CheckConstraint(
                condition=Q(cod_collected__isnull=True)
                | (Q(outcome=TaskStatus.SUCCEEDED) & Q(cod_collected=models.F("cod_expected"))),
                name="taskresult_cod_only_success_matching",
            ),
        ]

    def __str__(self):
        return f"{self.task_id} · {self.get_outcome_display()}"


class Handover(models.Model):
    """Bàn giao hàng: nhập điểm tập kết (UC04.10), tiếp nhận hàng hoàn (UC04.9), Shop nhận hàng hoàn (UC04.11).

    Chỉ thêm, không sửa/xóa. `received_by` luôn là Nhân viên ghi nhận.
    """

    shipment = models.ForeignKey(Shipment, verbose_name="vận đơn", on_delete=models.PROTECT,
                                 related_name="handovers")
    task = models.ForeignKey(Task, verbose_name="nhiệm vụ", on_delete=models.PROTECT, null=True, blank=True,
                             related_name="handovers", db_index=False)
    kind = models.CharField("loại", max_length=30, choices=HandoverKind.choices)
    from_shipper = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người giao", on_delete=models.PROTECT, null=True, blank=True,
        related_name="+", db_index=False,
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="nhân viên ghi nhận", on_delete=models.PROTECT, related_name="+",
        db_index=False,
    )
    received_at = models.DateTimeField("nhận lúc", default=timezone.now)
    # Spec 008: chỉ SHOP_PICKUP — người nhận phía Shop (có thể là người được ủy quyền, không phải tài khoản).
    receiver_name = models.CharField("người nhận (Shop)", max_length=RECEIVER_NAME_MAX_LENGTH, null=True,
                                     blank=True)
    discrepancy_note = models.CharField("ghi chú sai lệch", max_length=HANDOVER_NOTE_MAX_LENGTH, blank=True,
                                        default="")

    class Meta:
        verbose_name = "bàn giao"
        verbose_name_plural = "bàn giao"
        ordering = ["-received_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(kind__in=HandoverKind.values), name="handover_kind_valid"),
            # Spec 008 D7: tên người nhận phía Shop có (khác rỗng) ⇔ Shop nhận hàng hoàn. isnull tường minh —
            # so sánh với NULL ra NULL và CHECK sẽ cho qua (bài học spec 007).
            models.CheckConstraint(
                condition=(Q(kind=HandoverKind.SHOP_PICKUP) & Q(receiver_name__isnull=False)
                           & ~Q(receiver_name=""))
                | (~Q(kind=HandoverKind.SHOP_PICKUP) & Q(receiver_name__isnull=True)),
                name="handover_receiver_only_shop_pickup",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.shipment_id}"
