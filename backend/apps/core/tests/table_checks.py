"""Kiểm tra toàn vẹn dùng chung cho mọi bảng chuyển trạng thái."""
from collections import deque

from apps.accounts.constants import UserRole
from apps.core.transitions import KEEP


class TransitionTableChecks:
    """Mixin cho SimpleTestCase. Lớp con khai báo các thuộc tính bên dưới."""

    table = None            # dict action -> Transition
    status_enum = None      # TextChoices trạng thái
    action_enum = None      # TextChoices hành động
    terminal = None         # frozenset trạng thái kết thúc
    initial = None          # trạng thái khởi đầu

    def test_every_action_has_rule_and_vice_versa(self):
        self.assertEqual(set(self.table), set(self.action_enum.values))

    def test_sources_and_targets_are_valid_statuses(self):
        statuses = set(self.status_enum.values)
        for action, rule in self.table.items():
            with self.subTest(action=action):
                # KEEP (spec 009 D2) = ở nguyên trạng thái nguồn → luôn hợp lệ nếu nguồn hợp lệ và không rỗng.
                if rule.target == KEEP:
                    self.assertTrue(rule.sources)
                else:
                    self.assertIn(rule.target, statuses)
                self.assertLessEqual(set(rule.sources), statuses)

    def test_roles_are_valid(self):
        for action, rule in self.table.items():
            with self.subTest(action=action):
                self.assertTrue(rule.roles)
                self.assertLessEqual(set(rule.roles), set(UserRole.values))

    def test_terminal_statuses_have_no_outgoing_action(self):
        for action, rule in self.table.items():
            with self.subTest(action=action):
                self.assertFalse(set(rule.sources) & self.terminal)

    def test_non_terminal_statuses_have_outgoing_action(self):
        sources = set().union(*(rule.sources for rule in self.table.values()))
        for status in set(self.status_enum.values) - self.terminal:
            with self.subTest(status=status):
                self.assertIn(status, sources)

    def test_terminal_set_is_subset_of_enum(self):
        self.assertLessEqual(self.terminal, set(self.status_enum.values))
        self.assertNotIn(self.initial, self.terminal)

    def _next(self, current):
        """Trạng thái đi tới được từ `current` trong một bước (KEEP = đứng yên, không thêm cạnh mới)."""
        return {rule.target_from(current) for rule in self.table.values() if current in rule.sources}

    def test_every_status_reachable_from_initial(self):
        seen, queue = {self.initial}, deque([self.initial])
        while queue:
            current = queue.popleft()
            for nxt in self._next(current) - seen:
                seen.add(nxt)
                queue.append(nxt)
        self.assertEqual(seen, set(self.status_enum.values))

    def test_every_non_terminal_status_can_reach_terminal(self):
        """Không có trạng thái 'kẹt' đi vòng mãi không kết thúc được."""
        for start in set(self.status_enum.values) - self.terminal:
            seen, queue = {start}, deque([start])
            while queue:
                current = queue.popleft()
                for nxt in self._next(current) - seen:
                    seen.add(nxt)
                    queue.append(nxt)
            with self.subTest(status=start):
                self.assertTrue(seen & self.terminal)
