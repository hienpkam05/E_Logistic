"""Phạm vi nhiệm vụ theo vai trò (phân quyền quy tắc 2): Shipper chỉ nhiệm vụ của mình (UC04.1 BR1)."""
from apps.accounts.constants import UserRole

from .models import Task


def tasks_visible_to(user):
    if user.role == UserRole.SHIPPER:
        return Task.objects.filter(shipper=user)
    if user.role == UserRole.ADMIN:
        return Task.objects.all()
    return Task.objects.none()
