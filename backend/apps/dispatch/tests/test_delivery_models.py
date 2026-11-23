"""Spec 007 Phase 1: ràng buộc DB cho giao hàng, COD, số lần giao (lớp chặn cuối, spec 001 mục 3.6 điểm 4)."""
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.dispatch.constants import (
    FAIL_REASONS_BY_TASK_TYPE,
    MAX_DELIVERY_ATTEMPTS,
    TASK_RESULT_REASON_CHOICES,
    DeliveryFailReason,
    PickupFailReason,
    TaskStatus,
    TaskType,
)
from apps.dispatch.models import Task, TaskResult
from apps.shipments import constants as shipment_constants
from apps.shipments.models import Shipment
from apps.shipments.tests.factories import make_shipment, make_user, make_ward


class Base(TestCase):
    def setUp(self):
        self.shop = make_user("shop_a", "0900000001")
        self.admin = make_user("nv_a", "0900000003", UserRole.ADMIN)
        self.shipper = make_user("sp_a", "0900000004", UserRole.SHIPPER)
        self.shipment = make_shipment(self.shop, make_ward())

    def task(self, **extra):
        data = {"shipment": self.shipment, "type": TaskType.DELIVERY, "attempt_no": 1, "shipper": self.shipper,
                "assigned_by": self.admin, **extra}
        return Task.objects.create(**data)

    def assert_rejected(self, fn):
        with self.assertRaises(IntegrityError), transaction.atomic():
            fn()


class AttemptConstraintTests(Base):
    def test_delivery_task_requires_attempt_in_range(self):
        """D1: phân công giao luôn ghi số thứ tự lần giao 1..3; thiếu / ngoài khoảng bị DB chặn."""
        self.assert_rejected(lambda: self.task(attempt_no=None))
        self.assert_rejected(lambda: self.task(attempt_no=0))
        self.assert_rejected(lambda: self.task(attempt_no=MAX_DELIVERY_ATTEMPTS + 1))
        self.task(attempt_no=MAX_DELIVERY_ATTEMPTS)

    def test_other_types_have_no_attempt(self):
        for task_type in (TaskType.PICKUP, TaskType.RETURN):
            with self.subTest(task_type):
                self.assert_rejected(lambda: self.task(type=task_type, attempt_no=1))
        self.task(type=TaskType.PICKUP, attempt_no=None)

    def test_shipment_delivery_attempts_max(self):
        """D8: tối đa 3 lần giao thực tế; cột không âm có sẵn từ PositiveSmallInteger."""
        update = Shipment.objects.filter(pk=self.shipment.pk).update
        update(delivery_attempts=MAX_DELIVERY_ATTEMPTS)
        self.assert_rejected(lambda: update(delivery_attempts=MAX_DELIVERY_ATTEMPTS + 1))
        self.assert_rejected(lambda: update(delivery_attempts=-1))

    def test_limit_lives_in_shipments(self):
        """shipments không import dispatch; dispatch dùng lại đúng một hằng số."""
        self.assertIs(MAX_DELIVERY_ATTEMPTS, shipment_constants.MAX_DELIVERY_ATTEMPTS)
        self.assertEqual(MAX_DELIVERY_ATTEMPTS, 3)


class CodConstraintTests(Base):
    def setUp(self):
        super().setUp()
        self.closed = self.task(status=TaskStatus.SUCCEEDED, closed_at=timezone.now())

    def result(self, **extra):
        data = {"task": self.closed, "outcome": TaskStatus.SUCCEEDED, "recorded_by": self.shipper,
                "cod_expected": 350_000, "cod_collected": 350_000, **extra}
        return TaskResult.objects.create(**data)

    def test_success_with_matching_cod(self):
        result = self.result()
        self.assertEqual((result.cod_expected, result.cod_collected), (350_000, 350_000))

    def test_no_cod_order_records_zero(self):
        """UC04.5 A1 / UC04.7 A1: đơn không COD → phải thu = thực thu = 0 (khác với 'không có COD' = null)."""
        result = self.result(cod_expected=0, cod_collected=0)
        self.assertEqual((result.cod_expected, result.cod_collected), (0, 0))

    def test_partial_or_over_collection_rejected(self):
        """UC04.7 BR1: không thu một phần; thừa cũng không lưu."""
        self.assert_rejected(lambda: self.result(cod_collected=330_000))
        self.assert_rejected(lambda: self.result(cod_collected=370_000))

    def test_cod_columns_come_in_pair(self):
        self.assert_rejected(lambda: self.result(cod_collected=None))
        self.assert_rejected(lambda: self.result(cod_expected=None))

    def test_failed_result_cannot_carry_cod(self):
        """Giao thất bại không phát sinh khoản thu (UC04.5 E1.3, UC04.7 E1.3)."""
        self.assert_rejected(lambda: self.result(outcome=TaskStatus.FAILED,
                                                 reason_code=DeliveryFailReason.COD_NOT_READY))
        self.result(outcome=TaskStatus.FAILED, reason_code=DeliveryFailReason.COD_NOT_READY,
                    cod_expected=None, cod_collected=None)

    def test_pickup_success_without_cod(self):
        """Nhiệm vụ lấy (spec 006) vẫn ghi kết quả không COD."""
        self.result(cod_expected=None, cod_collected=None)

    def test_negative_cod_rejected(self):
        self.assert_rejected(lambda: self.result(cod_expected=-1, cod_collected=-1))


class FailReasonTests(TestCase):
    def test_delivery_reasons(self):
        self.assertEqual(DeliveryFailReason.values, [
            "RECEIVER_UNREACHABLE", "RECEIVER_RESCHEDULED", "RECEIVER_REFUSED", "COD_NOT_READY",
            "ADDRESS_NOT_FOUND", "OTHER",
        ])

    def test_shared_codes_have_same_label(self):
        """Hai nhóm chung một cột reason_code: một mã chỉ được mang một nghĩa (D4 — đã đổi WRONG_ADDRESS)."""
        labels = {}
        for enum in FAIL_REASONS_BY_TASK_TYPE.values():
            for value, label in enum.choices:
                self.assertEqual(labels.setdefault(value, label), label, value)
        self.assertEqual(set(PickupFailReason.values) & set(DeliveryFailReason.values), {"OTHER"})

    def test_result_choices_are_union_without_duplicates(self):
        values = [value for value, _ in TASK_RESULT_REASON_CHOICES]
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(set(values), set(PickupFailReason.values) | set(DeliveryFailReason.values))
        self.assertEqual(TaskResult._meta.get_field("reason_code").choices, TASK_RESULT_REASON_CHOICES)

    def test_every_failable_type_has_reasons(self):
        """TASK_FAIL áp dụng cho PICKUP, DELIVERY (spec 001) — RETURN không thất bại."""
        self.assertEqual(set(FAIL_REASONS_BY_TASK_TYPE), {TaskType.PICKUP, TaskType.DELIVERY})
