"""Đọc task mở và điểm gần nhất trong cùng snapshot SQL (UC03.3)."""
from datetime import timedelta

from django.db.models import F, FloatField, OuterRef, Subquery, Value
from django.db.models.functions import Cast, JSONObject
from django.db.models.lookups import LessThan

from apps.dispatch.constants import OPEN_TASK_STATUSES
from apps.dispatch.models import Task
from .constants import LOCATION_STALE_SECONDS
from .models import LocationPing


def latest_points(task_id):
    return LocationPing.objects.filter(task_id=task_id).order_by("-recorded_at", "-id")


def current_task_location(shipment_id, now):
    # JSON whitelist: không trả shipper_id hay danh tính người gửi. Cast Decimal thành JSON number.
    point = latest_points(OuterRef("pk")).annotate(payload=JSONObject(
        lat=Cast("lat", FloatField()), lng=Cast("lng", FloatField()),
        accuracy=Cast("accuracy_m", FloatField()), recorded_at=F("recorded_at"), received_at=F("received_at"),
        stale=LessThan(F("recorded_at"), Value(now - timedelta(seconds=LOCATION_STALE_SECONDS))),
    )).values("payload")[:1]
    return Task.objects.filter(shipment_id=shipment_id, status__in=OPEN_TASK_STATUSES).annotate(
        location=Subquery(point)).order_by().values("id", "type", "location")
