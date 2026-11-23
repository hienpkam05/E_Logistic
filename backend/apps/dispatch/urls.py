"""/api/v1/dispatch/… — phía điều phối. Thao tác của Nhân viên TRÊN ĐƠN đăng ký ở shipments/urls.py (cùng
khuôn /shipments/{id}/<hành động>/ với duyệt/từ chối — spec 006 D2)."""
from django.urls import path

from .views import (
    ConfirmDeliveryView,
    ConfirmPickupView,
    FailDeliveryView,
    FailPickupView,
    ReportReturnHandoverView,
    ShipperPickerView,
    TaskDetailView,
    TaskListView,
)

urlpatterns = [
    path("shippers/", ShipperPickerView.as_view(), name="dispatch-shippers"),
    # Phía Shipper
    path("tasks/", TaskListView.as_view(), name="task-list"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:pk>/confirm-pickup/", ConfirmPickupView.as_view(), name="task-confirm-pickup"),
    path("tasks/<int:pk>/fail-pickup/", FailPickupView.as_view(), name="task-fail-pickup"),
    path("tasks/<int:pk>/confirm-delivery/", ConfirmDeliveryView.as_view(), name="task-confirm-delivery"),  # spec 007
    path("tasks/<int:pk>/fail-delivery/", FailDeliveryView.as_view(), name="task-fail-delivery"),
    path("tasks/<int:pk>/report-return-handover/", ReportReturnHandoverView.as_view(),  # spec 008
         name="task-report-return-handover"),
]
