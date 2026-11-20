from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """Application liveness only; does not check database connectivity."""
    return JsonResponse({"status": "ok", "service": "htt-express-api"})
