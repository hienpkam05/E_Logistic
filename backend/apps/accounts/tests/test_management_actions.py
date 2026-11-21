"""Spec 003 Phase 3: khóa, mở khóa, đặt lại mật khẩu, lịch sử."""
import logging
import threading

from django.conf import settings
from django.core.cache import cache
from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts import services
from apps.accounts.constants import AccountAction, UserRole
from apps.accounts.models import AccountEvent, User
from apps.core.errors import BusinessError, ErrorCode

PASSWORD = "Matkhau@12345"
ME, LOGIN = reverse("me"), reverse("auth-login")


def url(name, pk):
    return reverse(name, args=[pk])


def make_user(username, phone, role, **extra):
    return User.objects.create_user(username=username, password=PASSWORD, full_name=f"Tên {username}",
                                    phone=phone, role=role, **extra)


def login(username, password=PASSWORD):
    client = Client()
    response = client.post(LOGIN, {"username": username, "password": password}, content_type="application/json")
    return client, response


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user("nv_a", "0900000001", UserRole.ADMIN)
        self.admin2 = make_user("nv_b", "0900000002", UserRole.ADMIN)
        self.shop = make_user("shop_hoa", "0900000003", UserRole.SHOP)
        self.shipper = make_user("shipper_long", "0900000004", UserRole.SHIPPER)
        self.client.force_login(self.admin)

    def post(self, name, pk, data=None, client=None):
        return (client or self.client).post(url(name, pk), data or {}, content_type="application/json")

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        body = response.json()["error"]
        self.assertEqual(body["code"], code)
        return body


class LockTests(Base):
    def test_lock_blocks_login_and_kills_sessions(self):
        shipper_client, _ = login("shipper_long")
        self.assertEqual(shipper_client.get(ME).status_code, 200)
        response = self.post("account-lock", self.shipper.pk, {"reason": "  Nghỉ việc  "})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_active"])
        self.assertEqual(shipper_client.get(ME).status_code, 401)
        _, relogin = login("shipper_long")
        self.assert_error(relogin, 400, ErrorCode.INVALID_CREDENTIALS)  # giống hệt sai mật khẩu
        event = AccountEvent.objects.get(account=self.shipper)
        self.assertEqual((event.action, event.actor, event.reason), (AccountAction.LOCKED, self.admin, "Nghỉ việc"))

    def test_unlock_requires_fresh_login(self):
        shipper_client, _ = login("shipper_long")
        old_cookie = shipper_client.cookies[settings.SESSION_COOKIE_NAME].value
        self.post("account-lock", self.shipper.pk)
        response = self.post("account-unlock", self.shipper.pk)
        self.assertTrue(response.json()["is_active"])
        replay = Client()
        replay.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
        self.assertEqual(replay.get(ME).status_code, 401)  # UC06.4 A1.3
        fresh, login_response = login("shipper_long")
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(fresh.get(ME).status_code, 200)
        self.assertEqual(list(AccountEvent.objects.filter(account=self.shipper).order_by("id")
                              .values_list("action", flat=True)), [AccountAction.LOCKED, AccountAction.UNLOCKED])

    def test_repeat_lock_unlock_is_idempotent(self):
        for _ in range(2):
            self.assertEqual(self.post("account-lock", self.shipper.pk).status_code, 200)
        for _ in range(2):
            self.assertEqual(self.post("account-unlock", self.shipper.pk).status_code, 200)
        self.assertEqual(AccountEvent.objects.filter(account=self.shipper).count(), 2)
        self.shipper.refresh_from_db()
        self.assertEqual(self.shipper.session_version, 1)  # khóa lặp không tăng thêm

    def test_reason_optional_and_limited(self):
        self.assertEqual(self.post("account-lock", self.shop.pk).status_code, 200)
        self.post("account-unlock", self.shop.pk)
        err = self.assert_error(self.post("account-lock", self.shop.pk, {"reason": "x" * 256}), 400,
                                ErrorCode.VALIDATION_ERROR)
        self.assertIn("reason", err["fields"])

    def test_can_lock_other_admin_but_not_last_one(self):
        self.assertEqual(self.post("account-lock", self.admin2.pk).status_code, 200)
        # admin là ADMIN hoạt động duy nhất; tự khóa bị chặn trước (D1), nên thử qua service với người khác
        root = User.objects.create_superuser(username="root", password=PASSWORD, full_name="Root", phone="0900000099")
        User.objects.filter(pk=root.pk).update(is_active=False)  # không tính là Admin hoạt động
        with self.assertRaises(BusinessError) as ctx:
            services.lock_account(root, self.admin.pk)
        self.assertEqual(ctx.exception.code, ErrorCode.LIMIT_REACHED)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_last_admin_via_api(self):
        self.post("account-lock", self.admin2.pk)
        other = make_user("nv_c", "0900000005", UserRole.ADMIN)
        client = Client()
        client.force_login(other)
        self.assertEqual(self.post("account-lock", self.admin.pk, client=client).status_code, 200)
        # còn mỗi nv_c hoạt động; nv_c không tự khóa được (403) — hệ thống luôn còn ít nhất 1 Admin
        self.assert_error(self.post("account-lock", other.pk, client=client), 403, ErrorCode.PERMISSION_DENIED)
        self.assertEqual(User.objects.filter(role=UserRole.ADMIN, is_active=True).count(), 1)

    def test_locked_admin_unlock_restores(self):
        self.post("account-lock", self.admin2.pk)
        self.assertTrue(self.post("account-unlock", self.admin2.pk).json()["is_active"])

    def test_cannot_act_on_self(self):
        for name, data in (("account-lock", {}), ("account-unlock", {}),
                           ("account-reset-password", {"identity_verified": True})):
            with self.subTest(name=name):
                err = self.assert_error(self.post(name, self.admin.pk, data), 403, ErrorCode.PERMISSION_DENIED)
                self.assertIn("Thông tin cá nhân", err["message"])

    def test_not_found(self):
        for name in ("account-lock", "account-unlock", "account-reset-password"):
            with self.subTest(name=name):
                self.assert_error(self.post(name, 999999, {"identity_verified": True}), 404, ErrorCode.NOT_FOUND)

    def test_hook_runs_inside_transaction(self):
        seen = []
        services._account_locked_hooks[:] = [lambda actor, user: seen.append((actor.pk, user.pk, user.is_active))]
        try:
            self.post("account-lock", self.shipper.pk)
        finally:
            services._account_locked_hooks.clear()
        self.assertEqual(seen, [(self.admin.pk, self.shipper.pk, False)])

    def test_failing_hook_rolls_back_lock(self):
        def boom(actor, user):
            raise RuntimeError("spec 006 lỗi")

        services._account_locked_hooks[:] = [boom]
        try:
            with self.assertRaises(RuntimeError):
                services.lock_account(self.admin, self.shipper.pk)
        finally:
            services._account_locked_hooks.clear()
        self.shipper.refresh_from_db()
        self.assertTrue(self.shipper.is_active)
        self.assertEqual(self.shipper.session_version, 0)
        self.assertFalse(AccountEvent.objects.exists())


class ResetPasswordTests(Base):
    def test_requires_identity_verified(self):
        for data in ({}, {"identity_verified": False}):
            with self.subTest(data=data):
                err = self.assert_error(self.post("account-reset-password", self.shop.pk, data), 400,
                                        ErrorCode.VALIDATION_ERROR)
                self.assertEqual(err["fields"]["identity_verified"], ["Cần xác minh danh tính trước khi đặt lại mật khẩu."])
        self.shop.refresh_from_db()
        self.assertTrue(self.shop.check_password(PASSWORD))

    def test_reset_issues_temp_password_and_kills_sessions(self):
        shop_client, _ = login("shop_hoa")
        response = self.post("account-reset-password", self.shop.pk, {"identity_verified": True})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"user", "temp_password"})
        self.assertTrue(body["user"]["must_change_password"])
        self.assertEqual(shop_client.get(ME).status_code, 401)  # phiên cũ mất
        self.assert_error(login("shop_hoa")[1], 400, ErrorCode.INVALID_CREDENTIALS)  # mật khẩu cũ hết dùng
        fresh, response = login("shop_hoa", body["temp_password"])
        self.assertTrue(response.json()["must_change_password"])
        self.assert_error(fresh.get(reverse("notification-list")), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)

    def test_event_has_no_password(self):
        temp = self.post("account-reset-password", self.shop.pk, {"identity_verified": True}).json()["temp_password"]
        event = AccountEvent.objects.get(account=self.shop)
        self.assertEqual(event.action, AccountAction.PASSWORD_RESET)
        self.assertEqual(event.changes, {"identity_verified": True})
        events_body = self.client.get(url("account-events", self.shop.pk)).content.decode()
        self.assertNotIn(temp, events_body)

    def test_reset_locked_account_allowed(self):
        self.post("account-lock", self.shipper.pk)
        body = self.post("account-reset-password", self.shipper.pk, {"identity_verified": True}).json()
        self.assertFalse(body["user"]["is_active"])
        self.assert_error(login("shipper_long", body["temp_password"])[1], 400, ErrorCode.INVALID_CREDENTIALS)
        self.post("account-unlock", self.shipper.pk)
        self.assertEqual(login("shipper_long", body["temp_password"])[1].status_code, 200)

    def test_temp_password_not_logged(self):
        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger("kiem_tra").debug("bắt đầu")
            temp = self.post("account-reset-password", self.shop.pk, {"identity_verified": True}).json()["temp_password"]
        self.assertNotIn(temp, "\n".join(logs.output))


class EventListTests(Base):
    def test_history_newest_first_with_actor(self):
        self.post("account-lock", self.shipper.pk, {"reason": "Tạm nghỉ"})
        self.post("account-unlock", self.shipper.pk)
        AccountEvent.objects.create(account=self.shipper, action=AccountAction.PASSWORD_RESET)  # thao tác hệ thống
        body = self.client.get(url("account-events", self.shipper.pk)).json()
        self.assertEqual(body["count"], 3)
        first, _, last = body["results"]
        self.assertEqual(set(first), {"id", "action", "actor", "changes", "reason", "created_at"})
        self.assertEqual((first["action"], first["actor"]), ("PASSWORD_RESET", None))
        self.assertEqual(last["action"], "LOCKED")
        self.assertEqual(last["reason"], "Tạm nghỉ")
        self.assertEqual(last["actor"], {"id": self.admin.pk, "username": "nv_a", "full_name": "Tên nv_a"})

    def test_only_this_account_and_query_count_constant(self):
        self.post("account-lock", self.shop.pk)

        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(url("account-events", self.shipper.pk)).status_code, 200)
            return len(ctx)

        self.assertEqual(self.client.get(url("account-events", self.shipper.pk)).json()["count"], 0)
        # Đo từ 1 bản ghi: trang rỗng Django bỏ hẳn câu truy vấn dữ liệu nên luôn ít hơn 1 câu.
        AccountEvent.objects.create(account=self.shipper, actor=self.admin, action=AccountAction.UPDATED)
        few = count()
        for _ in range(10):
            AccountEvent.objects.create(account=self.shipper, actor=self.admin2, action=AccountAction.UPDATED)
        self.assertEqual(count(), few)  # select_related actor, không N+1

    def test_read_only_and_not_found(self):
        self.assert_error(self.client.post(url("account-events", self.shop.pk)), 405, ErrorCode.REQUEST_ERROR)
        self.assert_error(self.client.get(url("account-events", 999999)), 404, ErrorCode.NOT_FOUND)

    def test_non_admin_forbidden(self):
        for user in (self.shop, self.shipper):
            client = Client()
            client.force_login(user)
            for response in (client.get(url("account-events", self.shop.pk)),
                             self.post("account-lock", self.shop.pk, client=client),
                             self.post("account-unlock", self.shop.pk, client=client),
                             self.post("account-reset-password", self.shop.pk, {"identity_verified": True}, client)):
                self.assert_error(response, 403, ErrorCode.PERMISSION_DENIED)


class ConcurrentLastAdminTests(TransactionTestCase):
    """Hai Admin cuối cùng khóa nhau cùng lúc (2 luồng, 2 kết nối DB thật): đúng một người thành công."""

    def test_two_admins_lock_each_other_simultaneously(self):
        a = make_user("nv_a", "0900000001", UserRole.ADMIN)
        b = make_user("nv_b", "0900000002", UserRole.ADMIN)
        barrier = threading.Barrier(2)
        results = {}

        def worker(actor, target):
            try:
                barrier.wait(timeout=10)
                services.lock_account(actor, target.pk)
                results[actor.username] = "ok"
            except BusinessError as exc:
                results[actor.username] = exc.code
            except Exception as exc:  # deadlock hoặc lỗi khác sẽ lộ ra ở đây
                results[actor.username] = repr(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker, args=(a, b)), threading.Thread(target=worker, args=(b, a))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertEqual(sorted(results.values()), sorted(["ok", ErrorCode.LIMIT_REACHED]), results)
        self.assertEqual(User.objects.filter(role=UserRole.ADMIN, is_active=True).count(), 1)
