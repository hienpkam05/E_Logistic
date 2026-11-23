"""Định dạng hiển thị dùng trong thông điệp backend — khớp frontend (utils/format.js) để người dùng thấy một kiểu."""
VND_SYMBOL = "₫"
THOUSANDS_SEPARATOR = "."


def format_vnd(amount):
    """350000 -> "350.000 ₫" (như Intl vi-VN ở frontend)."""
    return f"{int(amount):,}".replace(",", THOUSANDS_SEPARATOR) + f" {VND_SYMBOL}"
