from django.urls import path

from .views import (
    AccountCollectionView,
    AccountDetailView,
    AccountEventListView,
    AccountLockView,
    AccountResetPasswordView,
    AccountUnlockView,
    ChangePasswordView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
)

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="me"),
    path("me/password/", ChangePasswordView.as_view(), name="me-password"),
    # Spec 003 — quản lý tài khoản (chỉ ADMIN)
    path("users/", AccountCollectionView.as_view(), name="account-list"),
    path("users/<int:pk>/", AccountDetailView.as_view(), name="account-detail"),
    path("users/<int:pk>/lock/", AccountLockView.as_view(), name="account-lock"),
    path("users/<int:pk>/unlock/", AccountUnlockView.as_view(), name="account-unlock"),
    path("users/<int:pk>/reset-password/", AccountResetPasswordView.as_view(), name="account-reset-password"),
    path("users/<int:pk>/events/", AccountEventListView.as_view(), name="account-events"),
]
