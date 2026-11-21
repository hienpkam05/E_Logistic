from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.accounts.permissions import ALLOW_FLAG, PasswordChangeNotRequired
from apps.core.errors import ErrorCode

PASSWORD = "Matkhau@12345"
ME_FIELDS = {"id", "username", "full_name", "phone", "address", "role", "must_change_password", "date_joined"}
LOGIN, LOGOUT, ME, CSRF = reverse("auth-login"), reverse("auth-logout"), reverse("me"), reverse("auth-csrf")


def make_user(username, role, phone, **extra):
    return User.objects.create_user(
        username=username, password=PASSWORD, full_name=username.title(), phone=phone, role=role, **extra
    )


class AuthTestCase(TestCase):
    def setUp(self):
        cache.clear()  # bộ đếm throttle đăng nhập
        self.shop = make_user("shop_a", UserRole.SHOP, "0900000001")
        self.admin = make_user("nv_a", UserRole.ADMIN, "0900000002")
        self.shipper = make_user("shipper_a", UserRole.SHIPPER, "0900000003")

    def login(self, username, password=PASSWORD, client=None):
        return (client or self.client).post(LOGIN, {"username": username, "password": password},
                                            content_type="application/json")

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)
        return response.json()["error"]


class LoginTests(AuthTestCase):
    def test_three_roles_login_and_get_role_from_account(self):
        for user in (self.shop, self.admin, self.shipper):
            with self.subTest(role=user.role):
                client = Client()
                response = self.login(user.username, client=client)
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(set(body), ME_FIELDS)
                self.assertEqual(body["role"], user.role)
                self.assertIn(settings.SESSION_COOKIE_NAME, response.cookies)
                self.assertEqual(client.get(ME).json()["username"], user.username)

    def test_role_in_request_body_is_ignored(self):
        response = self.client.post(LOGIN, {"username": "shop_a", "password": PASSWORD, "role": "ADMIN"},
                                    content_type="application/json")
        self.assertEqual(response.json()["role"], UserRole.SHOP)

    def test_wrong_password_unknown_user_locked_account_look_identical(self):
        make_user("locked", UserRole.SHOP, "0900000009", is_active=False)
        errors = []
        for username, password in (("shop_a", "sai-mat-khau"), ("khong_ton_tai", PASSWORD), ("locked", PASSWORD)):
            with self.subTest(username=username):
                response = self.login(username, password)
                errors.append(self.assert_error(response, 400, ErrorCode.INVALID_CREDENTIALS))
                self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertEqual(len({e["message"] for e in errors}), 1)
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_missing_fields(self):
        err = self.assert_error(self.client.post(LOGIN, {}, content_type="application/json"), 400,
                                ErrorCode.VALIDATION_ERROR)
        self.assertEqual(set(err["fields"]), {"username", "password"})

    def test_session_key_rotates_on_login(self):
        session = self.client.session
        session["truoc_dang_nhap"] = 1
        session.save()
        before = session.session_key
        self.login("shop_a")
        self.assertNotEqual(self.client.session.session_key, before)

    def test_password_never_in_response(self):
        response = self.login("shop_a")
        self.assertNotIn(PASSWORD, response.content.decode())
        self.assertNotIn("password", response.json())


class CsrfTests(AuthTestCase):
    def test_csrf_endpoint_sets_cookie(self):
        response = Client(enforce_csrf_checks=True).get(CSRF)
        self.assertEqual(response.status_code, 204)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_login_without_csrf_token_rejected_as_json(self):
        client = Client(enforce_csrf_checks=True)
        response = self.login("shop_a", client=client)
        self.assert_error(response, 403, ErrorCode.PERMISSION_DENIED)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    def test_login_with_csrf_flow_ok(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get(CSRF).cookies[settings.CSRF_COOKIE_NAME].value
        response = client.post(LOGIN, {"username": "shop_a", "password": PASSWORD},
                               content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def login_like_browser(self, host, origin):
        """Trình duyệt luôn gửi Origin với POST; Django so Origin với Host nhận được."""
        client = Client(enforce_csrf_checks=True, HTTP_HOST=host)
        token = client.get(CSRF).cookies[settings.CSRF_COOKIE_NAME].value
        return client.post(LOGIN, {"username": "shop_a", "password": PASSWORD}, content_type="application/json",
                           HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=origin)

    def test_browser_origin_same_as_host_ok(self):
        """Qua proxy Vite giữ Host (changeOrigin: false) hoặc reverse proxy cùng domain."""
        self.assertEqual(self.login_like_browser("127.0.0.1:5173", "http://127.0.0.1:5173").status_code, 200)

    def test_browser_origin_different_from_host_rejected(self):
        """Proxy đổi Host (changeOrigin: true) hoặc trang lạ gọi sang → CSRF từ chối (lỗi người dùng gặp 21/11)."""
        response = self.login_like_browser("127.0.0.1:8000", "http://127.0.0.1:5173")
        self.assert_error(response, 403, ErrorCode.PERMISSION_DENIED)
        response = self.login_like_browser("127.0.0.1:8000", "http://evil.example.com")
        self.assert_error(response, 403, ErrorCode.PERMISSION_DENIED)

    def test_logout_requires_csrf_when_logged_in(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.shop)
        self.assert_error(client.post(LOGOUT), 403, ErrorCode.PERMISSION_DENIED)
        self.assertEqual(client.get(ME).status_code, 200)  # vẫn đăng nhập


class ThrottleTests(AuthTestCase):
    def test_login_rate_limited_per_ip(self):
        rate = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"].split("/")[0])
        for _ in range(rate):
            self.login("shop_a", "sai")
        response = self.login("shop_a")  # kể cả mật khẩu đúng
        self.assert_error(response, 429, ErrorCode.REQUEST_ERROR)
        self.assertIn("Retry-After", response)
        # IP khác không bị ảnh hưởng
        other = Client(REMOTE_ADDR="10.0.0.2")
        self.assertEqual(self.login("shop_a", client=other).status_code, 200)


class LogoutAndSessionTests(AuthTestCase):
    def test_old_session_cookie_unusable_after_logout(self):
        self.login("shop_a")
        old_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(self.client.post(LOGOUT).status_code, 204)
        replay = Client()
        replay.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
        self.assert_error(replay.get(ME), 401, ErrorCode.NOT_AUTHENTICATED)

    def test_logout_when_not_logged_in_is_204(self):
        self.assertEqual(self.client.post(LOGOUT).status_code, 204)

    def test_locked_account_loses_session_on_next_request(self):
        self.login("shipper_a")
        self.assertEqual(self.client.get(ME).status_code, 200)
        User.objects.filter(pk=self.shipper.pk).update(is_active=False)
        self.assert_error(self.client.get(ME), 401, ErrorCode.NOT_AUTHENTICATED)

    def test_me_requires_login(self):
        self.assert_error(self.client.get(ME), 401, ErrorCode.NOT_AUTHENTICATED)

    def test_session_age_from_settings(self):
        self.login("shop_a")
        self.assertEqual(self.client.session.get_expiry_age(), settings.SESSION_COOKIE_AGE)

    def test_logout_hooks_run_and_failures_do_not_block(self):
        from apps.accounts import services

        called = []
        good = lambda user: called.append(user.username)  # noqa: E731

        def bad(user):
            raise RuntimeError("hook lỗi")

        services._logout_hooks[:] = [bad, good]
        try:
            self.login("shipper_a")
            with self.assertLogs("apps.accounts.services", level="ERROR"):
                self.assertEqual(self.client.post(LOGOUT).status_code, 204)
        finally:
            services._logout_hooks.clear()
        self.assertEqual(called, ["shipper_a"])
        self.assertEqual(self.client.get(ME).status_code, 401)


@override_settings(ROOT_URLCONF="apps.accounts.tests.gate_urls")
class PasswordChangeGateTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.temp = make_user("tam", UserRole.SHOP, "0900000010", must_change_password=True)
        self.client.force_login(self.temp)

    def test_blocks_default_and_role_views(self):
        for url in ("/t/default/", "/t/role/"):
            with self.subTest(url=url):
                self.assert_error(self.client.get(url), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)

    def test_allowed_endpoints(self):
        self.assertEqual(self.client.get(ME).json()["must_change_password"], True)
        self.assertEqual(self.client.get(reverse("meta-choices")).status_code, 200)
        self.assertEqual(self.client.get(CSRF).status_code, 204)
        self.assertEqual(self.client.post(LOGOUT).status_code, 204)

    def test_login_allowed_and_reports_flag(self):
        self.client.logout()
        self.assertTrue(self.login("tam").json()["must_change_password"])

    def test_normal_user_not_blocked(self):
        self.client.force_login(self.shop)
        self.assertEqual(self.client.get("/t/role/").status_code, 200)

    def test_anonymous_still_401(self):
        self.client.logout()
        self.assert_error(self.client.get("/t/role/"), 401, ErrorCode.NOT_AUTHENTICATED)


def iter_api_views(patterns=None, prefix=""):
    for entry in patterns if patterns is not None else get_resolver().url_patterns:
        if isinstance(entry, URLResolver):
            yield from iter_api_views(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            cls = getattr(entry.callback, "cls", None)
            if cls and issubclass(cls, APIView):
                yield prefix + str(entry.pattern), cls


class GateCoverageTests(TestCase):
    """Mọi API view phải chặn mật khẩu tạm, trừ view ghi rõ cờ cho phép (spec 002 D5)."""

    def test_every_api_view_enforces_gate_or_opts_out(self):
        views = list(iter_api_views())
        self.assertGreaterEqual(len(views), 5)
        missing = []
        for route, cls in views:
            perms = cls.permission_classes
            gated = any(isinstance(p, type) and issubclass(p, PasswordChangeNotRequired) for p in perms)
            opted_out = hasattr(cls, ALLOW_FLAG)
            if not (gated or opted_out):
                missing.append(route)
        self.assertEqual(missing, [], "View không chặn mật khẩu tạm và không khai báo cờ cho phép")

    def test_public_views_declare_flag(self):
        for route, cls in iter_api_views():
            if AllowAny in cls.permission_classes:
                with self.subTest(route=route):
                    self.assertTrue(hasattr(cls, ALLOW_FLAG), "View công khai phải khai báo cờ rõ ràng")
