"""Chuẩn hóa mọi lỗi API về {"error": {code, message, fields}}.

Đăng ký tại REST_FRAMEWORK["EXCEPTION_HANDLER"].
"""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import set_rollback

from .errors import DEFAULT_HTTP_STATUS, BusinessError, ErrorCode, error_payload

logger = logging.getLogger(__name__)


def _detail_text(detail):
    if isinstance(detail, (list, tuple)):
        return " ".join(str(item) for item in detail)
    return str(detail)


def _from_api_exception(exc):
    """Trả (code, message, fields, status) cho APIException của DRF."""
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        # SessionAuthentication không có WWW-Authenticate nên DRF trả 403; api.md quy định 401.
        return ErrorCode.NOT_AUTHENTICATED, None, {}, 401
    if isinstance(exc, exceptions.PermissionDenied):
        return ErrorCode.PERMISSION_DENIED, None, {}, 403
    if isinstance(exc, exceptions.NotFound):
        return ErrorCode.NOT_FOUND, None, {}, 404
    if isinstance(exc, exceptions.ValidationError):
        if isinstance(exc.detail, dict):
            return ErrorCode.VALIDATION_ERROR, None, exc.detail, 400
        return ErrorCode.VALIDATION_ERROR, _detail_text(exc.detail), {}, 400
    if isinstance(exc, exceptions.ParseError):
        return ErrorCode.VALIDATION_ERROR, _detail_text(exc.detail), {}, 400
    # 405, 406, 415, 429…: giữ mã HTTP gốc.
    return ErrorCode.REQUEST_ERROR, _detail_text(exc.detail), {}, exc.status_code


def api_exception_handler(exc, context):
    headers = {}

    if isinstance(exc, BusinessError):
        code, message, fields, status = exc.code, exc.message, exc.fields, exc.status
    elif isinstance(exc, Http404):
        code, message, fields, status = ErrorCode.NOT_FOUND, None, {}, 404
    elif isinstance(exc, DjangoPermissionDenied):
        code, message, fields, status = ErrorCode.PERMISSION_DENIED, None, {}, 403
    elif isinstance(exc, DjangoValidationError):
        fields = exc.message_dict if hasattr(exc, "error_dict") else {}
        message = None if fields else _detail_text(exc.messages)
        code, status = ErrorCode.VALIDATION_ERROR, 400
    elif isinstance(exc, exceptions.APIException):
        code, message, fields, status = _from_api_exception(exc)
        if getattr(exc, "wait", None):
            headers["Retry-After"] = str(int(exc.wait))
    else:
        # Lỗi không lường trước: ghi log đầy đủ, trả thông điệp chung, không lộ chi tiết.
        view = context.get("view")
        logger.exception("Lỗi không xử lý tại %s", type(view).__name__ if view else "?")
        code, message, fields, status = ErrorCode.SERVER_ERROR, None, {}, DEFAULT_HTTP_STATUS[ErrorCode.SERVER_ERROR]

    set_rollback()
    return Response(error_payload(code, message, fields), status=status, headers=headers)
