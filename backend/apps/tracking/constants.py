"""Giới hạn GPS (UC03.5, spec 011); một nguồn cho model, API và metadata."""
PING_MAX_AGE_SECONDS = 120
PING_MAX_FUTURE_SECONDS = 60
PING_MIN_INTERVAL_SECONDS = 15
PING_MAX_ACCURACY_M = 1000
LOCATION_STALE_SECONDS = 300
LOCATION_RETENTION_DAYS = 30
LOCATION_POLL_INTERVAL_SECONDS = 15
LAT_MIN, LAT_MAX = -90, 90
LNG_MIN, LNG_MAX = -180, 180

INVALID_NUMBER_MESSAGE = "Nhập số hữu hạn trong khoảng cho phép."
TIMEZONE_REQUIRED_MESSAGE = "Thời điểm đo phải có múi giờ."
INVALID_POINT_TIME_MESSAGE = "Thời điểm đo quá cũ, ở tương lai hoặc trước khi phân công nhiệm vụ."
