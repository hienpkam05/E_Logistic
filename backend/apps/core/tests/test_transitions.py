from django.test import SimpleTestCase

from apps.core.errors import BusinessError, ErrorCode
from apps.core.transitions import KEEP, allowed_actions, resolve_transition, transition

TABLE = {
    "CREATE": transition([], "NEW", ["SHOP"]),
    "APPROVE": transition(["NEW"], "APPROVED", ["ADMIN"]),
    "CLOSE": transition(["NEW", "APPROVED"], "CLOSED", ["ADMIN", "SHOP"]),
}


class ResolveTransitionTests(SimpleTestCase):
    def assert_business_error(self, code, *args):
        with self.assertRaises(BusinessError) as ctx:
            resolve_transition(TABLE, *args)
        self.assertEqual(ctx.exception.code, code)

    def test_valid_transition_returns_rule(self):
        rule = resolve_transition(TABLE, "APPROVE", "NEW", "ADMIN")
        self.assertEqual(rule.target, "APPROVED")

    def test_multiple_sources_and_roles(self):
        self.assertEqual(resolve_transition(TABLE, "CLOSE", "APPROVED", "SHOP").target, "CLOSED")

    def test_wrong_role_is_permission_denied(self):
        self.assert_business_error(ErrorCode.PERMISSION_DENIED, "APPROVE", "NEW", "SHOP")

    def test_wrong_source_is_invalid_transition(self):
        self.assert_business_error(ErrorCode.INVALID_TRANSITION, "APPROVE", "CLOSED", "ADMIN")

    def test_role_checked_before_state(self):
        # Sai cả hai: báo sai quyền, không tiết lộ trạng thái.
        self.assert_business_error(ErrorCode.PERMISSION_DENIED, "APPROVE", "CLOSED", "SHOP")

    def test_initial_action_requires_no_current_status(self):
        self.assertEqual(resolve_transition(TABLE, "CREATE", None, "SHOP").target, "NEW")
        self.assert_business_error(ErrorCode.INVALID_TRANSITION, "CREATE", "NEW", "SHOP")

    def test_none_status_rejected_for_non_initial_action(self):
        self.assert_business_error(ErrorCode.INVALID_TRANSITION, "APPROVE", None, "ADMIN")

    def test_unknown_action_is_programming_error(self):
        with self.assertRaises(ValueError):
            resolve_transition(TABLE, "KHONG_CO", "NEW", "ADMIN")


class AllowedActionsTests(SimpleTestCase):
    def test_lists_actions_for_role_and_status(self):
        self.assertEqual(allowed_actions(TABLE, "NEW", "ADMIN"), ["APPROVE", "CLOSE"])
        self.assertEqual(allowed_actions(TABLE, "NEW", "SHOP"), ["CLOSE"])

    def test_excludes_initial_actions_and_terminal(self):
        self.assertEqual(allowed_actions(TABLE, None, "SHOP"), [])
        self.assertEqual(allowed_actions(TABLE, "CLOSED", "ADMIN"), [])


class KeepTargetTests(SimpleTestCase):
    """Spec 009 D2: KEEP = ở nguyên trạng thái; không bao giờ lọt ra ngoài resolve_transition."""

    KEEP_TABLE = {**TABLE, "NOTE": transition(["NEW", "APPROVED"], KEEP, ["ADMIN"])}

    def test_resolve_replaces_keep_with_current_status(self):
        for status in ("NEW", "APPROVED"):
            with self.subTest(status=status):
                rule = resolve_transition(self.KEEP_TABLE, "NOTE", status, "ADMIN")
                self.assertEqual(rule.target, status)
                self.assertNotEqual(rule.target, KEEP)
        self.assertEqual(self.KEEP_TABLE["NOTE"].target, KEEP)  # bảng gốc không bị sửa (dataclass frozen + replace)

    def test_keep_still_checks_source_and_role(self):
        with self.assertRaises(BusinessError) as ctx:
            resolve_transition(self.KEEP_TABLE, "NOTE", "CLOSED", "ADMIN")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_TRANSITION)
        with self.assertRaises(BusinessError) as ctx:
            resolve_transition(self.KEEP_TABLE, "NOTE", "NEW", "SHOP")
        self.assertEqual(ctx.exception.code, ErrorCode.PERMISSION_DENIED)

    def test_allowed_actions_include_keep(self):
        self.assertIn("NOTE", allowed_actions(self.KEEP_TABLE, "APPROVED", "ADMIN"))
        self.assertNotIn("NOTE", allowed_actions(self.KEEP_TABLE, "CLOSED", "ADMIN"))

    def test_keep_needs_sources(self):
        with self.assertRaises(ValueError):
            transition([], KEEP, ["ADMIN"])

    def test_target_from(self):
        self.assertEqual(self.KEEP_TABLE["NOTE"].target_from("APPROVED"), "APPROVED")
        self.assertEqual(TABLE["APPROVE"].target_from("NEW"), "APPROVED")


class TableChecksStayStrictTests(SimpleTestCase):
    """Bộ kiểm bảng (TransitionTableChecks) phải còn bắt lỗi sau khi học KEEP — chạy nó trên bảng cố ý sai."""

    def run_checks(self, table, statuses, terminal=frozenset({"CLOSED"})):
        from django.db import models

        from apps.core.tests.table_checks import TransitionTableChecks

        status_enum = models.TextChoices("Status", [(s, s) for s in statuses])
        action_enum = models.TextChoices("Action", [(a, a) for a in table])

        class Probe(TransitionTableChecks, SimpleTestCase):
            pass

        Probe.table, Probe.status_enum, Probe.action_enum = table, status_enum, action_enum
        Probe.terminal, Probe.initial = terminal, "NEW"
        result = Probe("test_sources_and_targets_are_valid_statuses").run()
        for name in ("test_every_status_reachable_from_initial", "test_every_non_terminal_status_can_reach_terminal"):
            Probe(name).run(result)
        return result

    def test_good_table_with_keep_passes(self):
        table = {**TABLE, "NOTE": transition(["NEW", "APPROVED"], KEEP, ["ADMIN"])}
        result = self.run_checks(table, ["NEW", "APPROVED", "CLOSED"])
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)

    @staticmethod
    def failed(result):
        """Tên các kiểm tra báo lỗi — để khẳng định ĐÚNG kiểm tra nào bắt, không chỉ "có lỗi"."""
        # Lỗi trong subTest được báo bằng _SubTest (tên 'runTest') → lấy tên kiểm tra cha.
        return {getattr(test, "test_case", test)._testMethodName for test, _ in result.failures + result.errors}

    def test_unknown_target_caught_by_target_check(self):
        table = {**TABLE, "BAD": transition(["NEW"], "NOWHERE", ["ADMIN"])}
        self.assertIn("test_sources_and_targets_are_valid_statuses",
                      self.failed(self.run_checks(table, ["NEW", "APPROVED", "CLOSED"])))

    def test_status_reachable_only_by_keep_is_unreachable(self):
        """KEEP không tạo cạnh mới: trạng thái chỉ 'tới' bằng KEEP thì vẫn bị báo không tới được."""
        table = {**TABLE, "NOTE": transition(["ORPHAN"], KEEP, ["ADMIN"])}
        self.assertEqual(self.failed(self.run_checks(table, ["NEW", "APPROVED", "CLOSED", "ORPHAN"])),
                         {"test_every_status_reachable_from_initial",
                          "test_every_non_terminal_status_can_reach_terminal"})  # chỉ tự lặp → cũng không tới được kết thúc
