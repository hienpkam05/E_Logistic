"""Mã lỗi API và lỗi nghiệp vụ dùng chung. Định dạng phản hồi: specs/001-nen-tang/api.md."""
from django.db import models


class ErrorCode(models.TextChoices):
    # Nhãn là thông điệp mặc định khi không truyền message riêng.
    VALIDATION_ERROR = "VALIDATION_ERROR", "Dữ liệu chưa hợp lệ."
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED", "Bạn cần đăng nhập để tiếp tục."
    PERMISSION_DENIED = "PERMISSION_DENIED", "Bạn không có quyền thực hiện thao tác này."
    NOT_FOUND = "NOT_FOUND", "Không tìm thấy dữ liệu."
    INVALID_TRANSITION = "INVALID_TRANSITION", "Trạng thái hiện tại không cho phép thao tác này."
    CONFLICT = "CONFLICT", "Dữ liệu vừa được thay đổi. Vui lòng tải lại."
    LIMIT_REACHED = "LIMIT_REACHED", "Đã vượt giới hạn cho phép."
    REQUEST_ERROR = "REQUEST_ERROR", "Yêu cầu không được hỗ trợ."
    # Spec 002
    INVALID_CREDENTIALS = (
        "INVALID_CREDENTIALS",
        "Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản không thể đăng nhập. "
        "Vui lòng kiểm tra lại hoặc liên hệ Nhân viên.",
    )
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED", "Bạn cần đổi mật khẩu trước khi tiếp tục."
    SERVER_ERROR = "SERVER_ERROR", "Hệ thống gặp lỗi. Vui lòng thử lại sau."


DEFAULT_HTTP_STATUS = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.NOT_AUTHENTICATED: 401,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.INVALID_TRANSITION: 409,
    ErrorCode.CONFLICT: 409,
    ErrorCode.LIMIT_REACHED: 409,
    ErrorCode.REQUEST_ERROR: 400,
    ErrorCode.SERVER_ERROR: 500,
    ErrorCode.INVALID_CREDENTIALS: 400,
    ErrorCode.PASSWORD_CHANGE_REQUIRED: 403,
}


class BusinessError(Exception):
    """Lỗi nghiệp vụ do service raise; exception handler chuyển thành phản hồi chuẩn."""

    def __init__(self, code, message=None, *, fields=None, status=None):
        self.code = ErrorCode(code)
        self.message = message or self.code.label
        self.fields = fields or {}
        self.status = status or DEFAULT_HTTP_STATUS[self.code]
        super().__init__(self.message)


def error_payload(code, message=None, fields=None):
    code = ErrorCode(code)
    return {"error": {"code": code.value, "message": message or code.label, "fields": fields or {}}}
