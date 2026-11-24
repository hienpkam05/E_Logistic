"""Ghi GPS trong giao dịch với cùng thứ tự khóa của điều phối."""
from django.db import transaction
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.core.errors import BusinessError, ErrorCode
from apps.dispatch.constants import OPEN_TASK_STATUSES
from apps.dispatch.services import _lock_own_task

from .constants import INVALID_POINT_TIME_MESSAGE, PING_MAX_AGE_SECONDS, PING_MAX_FUTURE_SECONDS, PING_MIN_INTERVAL_SECONDS
from .models import LocationPing
from .serializers import LocationPingSerializer


@transaction.atomic
def record_location(shipper, task_id, payload):
    if shipper.role != UserRole.SHIPPER:
        raise BusinessError(ErrorCode.PERMISSION_DENIED)
    # Khóa đơn → user → task; kiểm lại active sau chờ khóa. User lock tránh đua FK khi khóa tài khoản.
    _, task = _lock_own_task(shipper, task_id, lock_actor=True)
    if task.status not in OPEN_TASK_STATUSES:
        raise BusinessError(ErrorCode.INVALID_TRANSITION)
    # Parse sau quyền/trạng thái để payload sai không làm lộ nhiệm vụ ngoài quyền.
    serializer = LocationPingSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    now = timezone.now()
    recorded_at = data["recorded_at"]
    age = (now - recorded_at).total_seconds()
    if age > PING_MAX_AGE_SECONDS or age < -PING_MAX_FUTURE_SECONDS or recorded_at < task.assigned_at:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, fields={"recorded_at": [INVALID_POINT_TIME_MESSAGE]})
    latest = task.location_pings.first()
    if latest is not None and (recorded_at <= latest.recorded_at
                               or (now - latest.received_at).total_seconds() < PING_MIN_INTERVAL_SECONDS):
        return False
    LocationPing.objects.create(task=task, shipper=shipper, lat=data["lat"], lng=data["lng"],
                                accuracy_m=data["accuracy"], recorded_at=recorded_at, received_at=now)
    return True
