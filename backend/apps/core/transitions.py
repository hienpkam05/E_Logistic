"""Helper chuyển trạng thái dùng chung cho vận đơn và nhiệm vụ.

Chỉ kiểm tra vai trò + trạng thái nguồn. Điều kiện nghiệp vụ khác (sở hữu, phân công,
giới hạn lần giao, COD…) kiểm tra trong service của từng app.
"""
from dataclasses import dataclass, replace

from .errors import BusinessError, ErrorCode

# Đích "ở nguyên trạng thái hiện tại" (spec 009 D2): thao tác không đổi trạng thái nhưng áp dụng cho NHIỀU trạng
# thái nguồn (vd nhận hàng về điểm tập kết khi Chờ giao lại hoặc Chờ xử lý hoàn). Chỉ tồn tại TRONG bảng:
# `resolve_transition` luôn trả đích là trạng thái thật, nên code ngoài bảng (gán `status = rule.target`) không bao
# giờ thấy giá trị này.
KEEP = "__KEEP__"


@dataclass(frozen=True)
class Transition:
    sources: frozenset  # rỗng = hành động khởi tạo (chưa có trạng thái)
    target: str
    roles: frozenset

    @property
    def is_initial(self):
        return not self.sources

    @property
    def keeps_status(self):
        return self.target == KEEP

    def target_from(self, source):
        """Trạng thái đích khi đi từ `source` (giải `KEEP`)."""
        return source if self.keeps_status else self.target


def transition(sources, target, roles):
    """Cú pháp gọn để khai báo bảng: transition([A, B], C, [ROLE]) hoặc transition([A, B], KEEP, [ROLE])."""
    if target == KEEP and not sources:
        raise ValueError("KEEP cần trạng thái nguồn (hành động khởi tạo không 'giữ nguyên' được).")
    return Transition(frozenset(sources), target, frozenset(roles))


def resolve_transition(table, action, current_status, role):
    """Trả Transition hợp lệ (đích là trạng thái thật — đã giải KEEP) hoặc raise BusinessError.

    - Hành động không có trong bảng: lỗi lập trình → ValueError.
    - Sai vai trò → PERMISSION_DENIED.
    - Trạng thái hiện tại không phải nguồn hợp lệ → INVALID_TRANSITION.
    """
    try:
        rule = table[action]
    except KeyError:
        raise ValueError(f"Hành động {action!r} không có trong bảng chuyển trạng thái.") from None

    if role not in rule.roles:
        raise BusinessError(ErrorCode.PERMISSION_DENIED)

    valid_source = current_status is None if rule.is_initial else current_status in rule.sources
    if not valid_source:
        raise BusinessError(ErrorCode.INVALID_TRANSITION)
    return replace(rule, target=rule.target_from(current_status)) if rule.keeps_status else rule


def allowed_actions(table, current_status, role):
    """Các hành động vai trò này được làm ở trạng thái hiện tại (để hiển thị nút thao tác).

    Chỉ dựa trên bảng; service vẫn phải kiểm tra điều kiện nghiệp vụ khi thực hiện.
    """
    return [
        action
        for action, rule in table.items()
        if role in rule.roles and not rule.is_initial and current_status in rule.sources
    ]
