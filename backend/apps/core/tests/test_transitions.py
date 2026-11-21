from django.test import SimpleTestCase

from apps.core.errors import BusinessError, ErrorCode
from apps.core.transitions import allowed_actions, resolve_transition, transition

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
