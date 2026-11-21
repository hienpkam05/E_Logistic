"""URL chỉ dùng trong test: các view cố tình gây từng loại lỗi."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.urls import include, path
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.constants import UserRole
from apps.accounts.permissions import HasRole
from apps.core.errors import BusinessError, ErrorCode


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=10)


@api_view(["POST"])
@permission_classes([AllowAny])
def validation_view(request):
    PhoneSerializer(data=request.data).is_valid(raise_exception=True)
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def business_view(request):
    raise BusinessError(ErrorCode.INVALID_TRANSITION, "Yêu cầu không còn ở trạng thái Chờ xác nhận.")


@api_view(["GET"])
@permission_classes([AllowAny])
def business_default_view(request):
    raise BusinessError(ErrorCode.LIMIT_REACHED)


@api_view(["GET"])
@permission_classes([AllowAny])
def django_validation_view(request):
    raise DjangoValidationError({"cod_amount": ["COD không được âm."]})


@api_view(["GET"])
def auth_required_view(request):  # dùng IsAuthenticated mặc định
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([HasRole.of(UserRole.ADMIN)])
def admin_only_view(request):
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def not_found_view(request):
    raise Http404("chi tiết nội bộ không được lộ")


@api_view(["GET"])
@permission_classes([AllowAny])
def crash_view(request):
    raise RuntimeError("bí mật nội bộ: password=abc")


class NumbersView(ListAPIView):
    permission_classes = [AllowAny]

    def get_queryset(self):
        return list(range(1, 251))

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(page)


urlpatterns = [
    path("t/validation/", validation_view),
    path("t/business/", business_view),
    path("t/business-default/", business_default_view),
    path("t/django-validation/", django_validation_view),
    path("t/auth/", auth_required_view),
    path("t/admin-only/", admin_only_view),
    path("t/not-found/", not_found_view),
    path("t/crash/", crash_view),
    path("t/numbers/", NumbersView.as_view()),
    path("", include("config.urls")),
]
