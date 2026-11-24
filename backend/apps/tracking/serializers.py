"""Đầu vào GPS: giữ timestamp thiết bị, kiểm biên trước khi làm tròn để lưu."""
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from .constants import (
    INVALID_NUMBER_MESSAGE, LAT_MIN, LAT_MAX, LNG_MIN, LNG_MAX,
    PING_MAX_ACCURACY_M, TIMEZONE_REQUIRED_MESSAGE,
)


class CoordinateField(serializers.Field):
    def __init__(self, *, minimum, maximum, places, **kwargs):
        self.minimum, self.maximum = Decimal(minimum), Decimal(maximum)
        self.quantum = Decimal(1).scaleb(-places)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            if isinstance(data, bool) or not isinstance(data, (str, int, float, Decimal)):
                raise ValueError
            value = Decimal(str(data))
            if not value.is_finite() or not self.minimum <= value <= self.maximum:
                raise ValueError
            return value.quantize(self.quantum)
        except (ValueError, InvalidOperation):
            raise serializers.ValidationError(INVALID_NUMBER_MESSAGE)


class AwareDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, data):
        try:
            parsed = parse_datetime(data) if isinstance(data, str) else None
        except (ValueError, TypeError):
            parsed = None
        if parsed is None or timezone.is_naive(parsed):
            raise serializers.ValidationError(TIMEZONE_REQUIRED_MESSAGE)
        return super().to_internal_value(data)


class LocationPingSerializer(serializers.Serializer):
    lat = CoordinateField(minimum=LAT_MIN, maximum=LAT_MAX, places=6)
    lng = CoordinateField(minimum=LNG_MIN, maximum=LNG_MAX, places=6)
    accuracy = CoordinateField(minimum=0, maximum=PING_MAX_ACCURACY_M, places=3,
                               required=False, allow_null=True, default=None)
    recorded_at = AwareDateTimeField()

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - self.fields.keys()
            if unknown:
                raise serializers.ValidationError({key: ["Trường không được hỗ trợ."] for key in sorted(unknown)})
        return super().to_internal_value(data)
