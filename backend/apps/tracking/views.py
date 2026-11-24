"""GPS: view được đăng ký dưới task để tái sử dụng tài nguyên nhiệm vụ."""
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.permissions import HasRole
from apps.shipments.permissions import shipments_visible_to
from .queries import current_task_location
from .services import record_location


class TaskLocationView(APIView):
    permission_classes = [HasRole.of(UserRole.SHIPPER)]

    def post(self, request, pk):
        stored = record_location(request.user, pk, request.data)
        return Response({"stored": stored}, status=201 if stored else 200)


class ShipmentLocationView(APIView):
    permission_classes = [HasRole.of(UserRole.SHOP, UserRole.ADMIN)]

    def get(self, request, pk):
        get_object_or_404(shipments_visible_to(request.user).only("pk"), pk=pk)
        current = current_task_location(pk, timezone.now()).first()
        if current is None:
            return Response({"task": None, "location": None})
        return Response({"task": {"id": current["id"], "type": current["type"]}, "location": current["location"]})
