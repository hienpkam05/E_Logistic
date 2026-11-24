"""Điểm GPS gắn nhiệm vụ; không cung cấp hành trình cá nhân (UC03.3–03.5)."""
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .constants import LAT_MIN, LAT_MAX, LNG_MIN, LNG_MAX, PING_MAX_ACCURACY_M


class LocationPing(models.Model):
    task = models.ForeignKey("dispatch.Task", on_delete=models.CASCADE, related_name="location_pings", db_index=False)
    shipper = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="location_pings", db_index=False)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_m = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    recorded_at = models.DateTimeField()
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at", "-id"]
        indexes = [
            models.Index(fields=["task", "-recorded_at", "-id"], name="location_task_latest_idx"),
            models.Index(fields=["received_at"], name="location_received_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(lat__gte=LAT_MIN, lat__lte=LAT_MAX), name="location_lat_valid"),
            models.CheckConstraint(condition=Q(lng__gte=LNG_MIN, lng__lte=LNG_MAX), name="location_lng_valid"),
            models.CheckConstraint(condition=Q(accuracy_m__isnull=True) | Q(accuracy_m__gte=0, accuracy_m__lte=PING_MAX_ACCURACY_M),
                                   name="location_accuracy_valid"),
        ]
