from django.test import SimpleTestCase

from apps.accounts.constants import UserRole
from apps.core.errors import BusinessError, ErrorCode
from apps.core.tests.table_checks import TransitionTableChecks
from apps.core.transitions import resolve_transition
from apps.dispatch import constants as c
from apps.dispatch.constants import TaskAction as A
from apps.dispatch.constants import TaskStatus as T


class TaskTransitionTableTests(TransitionTableChecks, SimpleTestCase):
    table = c.TASK_TRANSITIONS
    status_enum = T
    action_enum = A
    terminal = c.TERMINAL_TASK_STATUSES
    initial = c.INITIAL_TASK_STATUS

    def test_failed_task_never_becomes_replaced(self):
        # UC06.8 A2.3: nhiệm vụ đã thất bại giữ nguyên kết quả, không đổi thành Đã thay thế.
        for action, rule in self.table.items():
            with self.subTest(action=action):
                self.assertNotIn(T.FAILED, rule.sources)

    def test_swap_with_goods_requires_handover_before_replaced(self):
        self.assertEqual(resolve_transition(self.table, A.TASK_START_SWAP, T.ACTIVE, UserRole.ADMIN).target,
                         T.PENDING_SWAP_HANDOVER)
        # Trong lúc chờ bàn giao, không được ghi kết quả giao/lấy (phân quyền mục 5, quy tắc 12).
        for action in (A.TASK_SUCCEED, A.TASK_FAIL):
            with self.subTest(action=action), self.assertRaises(BusinessError) as ctx:
                resolve_transition(self.table, action, T.PENDING_SWAP_HANDOVER, UserRole.SHIPPER)
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_TRANSITION)

    def test_shipper_cannot_swap(self):
        with self.assertRaises(BusinessError) as ctx:
            resolve_transition(self.table, A.TASK_REPLACE, T.ACTIVE, UserRole.SHIPPER)
        self.assertEqual(ctx.exception.code, ErrorCode.PERMISSION_DENIED)

    def test_open_statuses(self):
        self.assertEqual(c.OPEN_TASK_STATUSES, {T.ACTIVE, T.PENDING_SWAP_HANDOVER})
        self.assertFalse(c.OPEN_TASK_STATUSES & c.TERMINAL_TASK_STATUSES)

    def test_max_delivery_attempts(self):
        self.assertEqual(c.MAX_DELIVERY_ATTEMPTS, 3)
