from django.test import SimpleTestCase

from apps.accounts.constants import UserRole
from apps.core.errors import BusinessError, ErrorCode
from apps.core.tests.table_checks import TransitionTableChecks
from apps.core.transitions import allowed_actions, resolve_transition
from apps.shipments import constants as c
from apps.shipments.constants import ShipmentAction as A
from apps.shipments.constants import ShipmentStatus as S

SHOP, ADMIN, SHIPPER = UserRole.SHOP, UserRole.ADMIN, UserRole.SHIPPER

# Bảng mục 4 docs/HTT_EXPRESS_Checklist_chuc_nang.md — đủ mọi dòng (dòng "Sửa yêu cầu" thêm ở spec 004).
# (trạng thái trước, trạng thái sau, vai trò). None = chưa có.
CHECKLIST_SECTION_4 = {
    (None, S.PENDING_APPROVAL, SHOP),                     # Tạo yêu cầu
    (S.PENDING_APPROVAL, S.PENDING_APPROVAL, SHOP),       # Sửa yêu cầu (UC05.1)
    (S.PENDING_APPROVAL, S.CANCELLED, SHOP),              # Hủy yêu cầu
    (S.PENDING_APPROVAL, S.REJECTED, ADMIN),              # Từ chối yêu cầu
    (S.PENDING_APPROVAL, S.AWAITING_PICKUP, ADMIN),       # Duyệt yêu cầu
    (S.AWAITING_PICKUP, S.PICKUP_ASSIGNED, ADMIN),        # Phân công lấy
    (S.PICKUP_ASSIGNED, S.PICKED_UP, SHIPPER),            # Lấy thành công
    (S.PICKUP_ASSIGNED, S.PICKUP_FAILED, SHIPPER),        # Lấy thất bại
    (S.PICKUP_FAILED, S.AWAITING_PICKUP, ADMIN),          # Quyết định lấy lại
    (S.PICKUP_FAILED, S.PICKUP_ABANDONED, ADMIN),         # Kết thúc không lấy được hàng
    (S.PICKED_UP, S.AT_HUB, ADMIN),                       # Nhận hàng tại điểm tập kết
    (S.AT_HUB, S.OUT_FOR_DELIVERY, ADMIN),                # Phân công giao lần đầu
    (S.OUT_FOR_DELIVERY, S.DELIVERED, SHIPPER),           # Giao thành công
    (S.OUT_FOR_DELIVERY, S.DELIVERY_FAILED, SHIPPER),     # Giao thất bại
    (S.DELIVERY_FAILED, S.AWAITING_REDELIVERY, ADMIN),    # Quyết định giao lại
    (S.AWAITING_REDELIVERY, S.OUT_FOR_DELIVERY, ADMIN),   # Phân công giao lại
    (S.DELIVERY_FAILED, S.AWAITING_RETURN, ADMIN),        # Quyết định hoàn
    (S.AWAITING_RETURN, S.RETURNING, ADMIN),              # Phân công hoàn
    (S.RETURNING, S.AWAITING_SHOP_PICKUP, ADMIN),         # Tiếp nhận hàng hoàn
    (S.AWAITING_RETURN, S.AWAITING_SHOP_PICKUP, ADMIN),   # Tiếp nhận hàng hoàn đã ở điểm tập kết (UC06.7 A1.2)
    (S.AWAITING_SHOP_PICKUP, S.RETURNED_TO_SHOP, ADMIN),  # Shop nhận hàng hoàn
    # Spec 008 — không đổi trạng thái nhưng cần mốc lịch sử (tiền lệ "Sửa yêu cầu" của spec 004):
    (S.RETURNING, S.RETURNING, SHIPPER),                  # Shipper báo đã đưa hàng hoàn về (UC04.9 bước 1–3, A1)
    (S.RETURNING, S.RETURNING, ADMIN),                    # NV ghi sai lệch, chưa nhận (UC04.9 E1)
}


def table_edges(table):
    edges = set()
    for rule in table.values():
        for source in rule.sources or [None]:
            for role in rule.roles:
                edges.add((source, rule.target, role))
    return edges


class ShipmentTransitionTableTests(TransitionTableChecks, SimpleTestCase):
    table = c.SHIPMENT_TRANSITIONS
    status_enum = S
    action_enum = A
    terminal = c.TERMINAL_SHIPMENT_STATUSES
    initial = c.INITIAL_SHIPMENT_STATUS

    def test_matches_checklist_exactly(self):
        edges = table_edges(self.table)
        self.assertEqual(CHECKLIST_SECTION_4 - edges, set(), "Thiếu so với checklist")
        self.assertEqual(edges - CHECKLIST_SECTION_4, set(), "Thừa so với checklist")

    def test_terminal_statuses(self):
        self.assertEqual(
            c.TERMINAL_SHIPMENT_STATUSES,
            {S.CANCELLED, S.REJECTED, S.PICKUP_ABANDONED, S.DELIVERED, S.RETURNED_TO_SHOP},
        )

    def test_shop_cannot_approve(self):
        with self.assertRaises(BusinessError) as ctx:
            resolve_transition(self.table, A.APPROVE_REQUEST, S.PENDING_APPROVAL, SHOP)
        self.assertEqual(ctx.exception.code, ErrorCode.PERMISSION_DENIED)

    def test_cannot_deliver_before_hub(self):
        # Phân công giao khi mới Đã lấy hàng (chưa nhập điểm tập kết) phải bị chặn — UC04.10 BR1.
        with self.assertRaises(BusinessError) as ctx:
            resolve_transition(self.table, A.ASSIGN_DELIVERY, S.PICKED_UP, ADMIN)
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_TRANSITION)

    def test_shipper_cannot_close_return(self):
        # Shipper không tự đặt Đã hoàn về Shop — UC04.9 BR1, UC04.11 BR1.
        with self.assertRaises(BusinessError):
            resolve_transition(self.table, A.CONFIRM_SHOP_RECEIVED, S.AWAITING_SHOP_PICKUP, SHIPPER)

    def test_shop_actions_while_pending(self):
        """UC05.4 bước 5: Chờ xác nhận thì Shop có Sửa + Hủy; sau duyệt thì không còn."""
        self.assertEqual(set(allowed_actions(self.table, S.PENDING_APPROVAL, SHOP)),
                         {A.UPDATE_REQUEST, A.CANCEL_REQUEST})
        self.assertEqual(allowed_actions(self.table, S.AWAITING_PICKUP, SHOP), [])

    def test_update_not_allowed_after_approval(self):
        with self.assertRaises(BusinessError) as ctx:
            resolve_transition(self.table, A.UPDATE_REQUEST, S.AWAITING_PICKUP, SHOP)
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_TRANSITION)

    def test_allowed_actions_after_delivery_failed(self):
        self.assertEqual(
            set(allowed_actions(self.table, S.DELIVERY_FAILED, ADMIN)),
            {A.DECIDE_REDELIVERY, A.DECIDE_RETURN},
        )
        self.assertEqual(allowed_actions(self.table, S.DELIVERY_FAILED, SHIPPER), [])

    def test_returning_actions_by_role(self):
        """Spec 008: Shipper chỉ báo bàn giao, không tự tiếp nhận (UC04.9 BR1); NV tiếp nhận hoặc ghi sai lệch."""
        self.assertEqual(set(allowed_actions(self.table, S.RETURNING, SHIPPER)), {A.REPORT_RETURN_HANDOVER})
        self.assertEqual(set(allowed_actions(self.table, S.RETURNING, ADMIN)), {A.RECEIVE_RETURN, A.REPORT_RETURN_ISSUE})
        self.assertEqual(allowed_actions(self.table, S.RETURNING, SHOP), [])
        for action in (A.REPORT_RETURN_HANDOVER, A.REPORT_RETURN_ISSUE):
            with self.subTest(action), self.assertRaises(BusinessError):
                resolve_transition(self.table, action, S.AWAITING_SHOP_PICKUP, ADMIN)  # chỉ khi Đang hoàn


class ShipmentConstantsTests(SimpleTestCase):
    def test_tracking_alphabet_has_no_ambiguous_chars(self):
        self.assertFalse(set("IO01") & set(c.TRACKING_CODE_ALPHABET))
        self.assertEqual(len(set(c.TRACKING_CODE_ALPHABET)), len(c.TRACKING_CODE_ALPHABET))

    def test_cod_max_positive_int(self):
        self.assertIsInstance(c.COD_MAX_VND, int)
        self.assertGreater(c.COD_MAX_VND, 0)
