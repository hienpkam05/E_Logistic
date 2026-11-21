from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .choices import build_choices
from .errors import ErrorCode, error_payload


@require_GET
def health(request):
    """Application liveness only; does not check database connectivity."""
    return JsonResponse({"status": "ok", "service": "htt-express-api"})


class ChoicesView(APIView):
    """Enum + giới hạn nghiệp vụ cho frontend. Công khai, không chứa dữ liệu nhạy cảm."""

    permission_classes = [AllowAny]
    allow_when_password_change_required = True

    def get(self, request):
        return Response(build_choices())


def api_not_found(request, *args, **kwargs):
    """Đường dẫn không tồn tại dưới /api/ trả JSON thay cho trang HTML 404."""
    # ensure_ascii=False: giữ UTF-8 như phản hồi của DRF, không escape \uXXXX.
    return JsonResponse(error_payload(ErrorCode.NOT_FOUND), status=404, json_dumps_params={"ensure_ascii": False})
