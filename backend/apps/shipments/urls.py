from django.urls import path

from apps.dispatch.views import (
    AbandonPickupView,
    AssignDeliveryView,
    AssignPickupView,
    AssignReturnView,
    ConfirmShopReceivedView,
    DecideRedeliveryView,
    DecideReturnView,
    ReceiveAtHubView,
    ReceiveReturnView,
    ReportReturnIssueView,
    RetryPickupView,
)

from .views import (
    ShipmentApproveView,
    ShipmentCancelView,
    ShipmentCollectionView,
    ShipmentDetailView,
    ShipmentEventListView,
    ShipmentRejectView,
    WardListView,
)

urlpatterns = [
    path("", ShipmentCollectionView.as_view(), name="shipment-list"),
    path("wards/", WardListView.as_view(), name="ward-list"),
    path("<int:pk>/", ShipmentDetailView.as_view(), name="shipment-detail"),
    path("<int:pk>/cancel/", ShipmentCancelView.as_view(), name="shipment-cancel"),
    path("<int:pk>/approve/", ShipmentApproveView.as_view(), name="shipment-approve"),
    path("<int:pk>/reject/", ShipmentRejectView.as_view(), name="shipment-reject"),
    # Spec 006 — điều phối lấy hàng (service ở apps.dispatch)
    path("<int:pk>/assign-pickup/", AssignPickupView.as_view(), name="shipment-assign-pickup"),
    path("<int:pk>/receive-at-hub/", ReceiveAtHubView.as_view(), name="shipment-receive-at-hub"),
    path("<int:pk>/retry-pickup/", RetryPickupView.as_view(), name="shipment-retry-pickup"),
    path("<int:pk>/abandon-pickup/", AbandonPickupView.as_view(), name="shipment-abandon-pickup"),
    # Spec 007 — giao hàng, giao lại / hoàn
    path("<int:pk>/assign-delivery/", AssignDeliveryView.as_view(), name="shipment-assign-delivery"),
    path("<int:pk>/decide-redelivery/", DecideRedeliveryView.as_view(), name="shipment-decide-redelivery"),
    path("<int:pk>/decide-return/", DecideReturnView.as_view(), name="shipment-decide-return"),
    # Spec 008 — hoàn hàng
    path("<int:pk>/assign-return/", AssignReturnView.as_view(), name="shipment-assign-return"),
    path("<int:pk>/receive-return/", ReceiveReturnView.as_view(), name="shipment-receive-return"),
    path("<int:pk>/report-return-issue/", ReportReturnIssueView.as_view(), name="shipment-report-return-issue"),
    path("<int:pk>/confirm-shop-received/", ConfirmShopReceivedView.as_view(), name="shipment-confirm-shop-received"),
    path("<int:pk>/events/", ShipmentEventListView.as_view(), name="shipment-events"),
]
