"""Helper chuyển trạng thái dùng chung cho vận đơn và nhiệm vụ.

Chỉ kiểm tra vai trò + trạng thái nguồn. Điều kiện nghiệp vụ khác (sở hữu, phân công,
giới hạn lần giao, COD…) kiểm tra trong service của từng app.
"""
from dataclasses import dataclass

from .errors import BusinessError, ErrorCode


@dataclass(frozen=True)
class Transition:
    sources: frozenset  # rỗng = hành động khởi tạo (chưa có trạng thái)
    target: str
    roles: frozenset

    @property
    def is_initial(self):
        return not self.sources


def transition(sources, target, roles):
    """Cú pháp gọn để khai báo bảng: transition([A, B], C, [ROLE])."""
    return Transition(frozenset(sources), target, frozenset(roles))


def resolve_transition(table, action, current_status, role):
    """Trả Transition hợp lệ hoặc raise BusinessError.

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
    return rule


def allowed_actions(table, current_status, role):
    """Các hành động vai trò này được làm ở trạng thái hiện tại (để hiển thị nút thao tác).

    Chỉ dựa trên bảng; service vẫn phải kiểm tra điều kiện nghiệp vụ khi thực hiện.
    """
    return [
        action
        for action, rule in table.items()
        if role in rule.roles and not rule.is_initial and current_status in rule.sources
    ]
