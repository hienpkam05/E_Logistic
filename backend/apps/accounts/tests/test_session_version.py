from django.conf import settings
from django.core.cache import cache
from django.db.models import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.constants import AccountAction, UserRole
from apps.accounts.models import AccountEvent, User

PASSWORD = "Matkhau@12345"
ME, LOGIN = reverse("me"), reverse("auth-login")


def make_user(username, phone, role=UserRole.SHIPPER, **extra):
    return User.objects.create_user(username=username, password=PASSWORD, full_name=username,
                                    phone=phone, role=role, **extra)


class SessionVersionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("shipper_a", "0900000001")

    def login(self, client=None):
        client = client or Client()
        response = client.post(LOGIN, {"username": "shipper_a", "password": PASSWORD}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        return client

    def test_hash_depends_on_session_version(self):
        before = self.user.get_session_auth_hash()
        self.user.invalidate_sessions()
        self.assertEqual(self.user.session_version, 1)
        self.assertNotEqual(self.user.get_session_auth_hash(), before)

    def test_invalidate_kills_all_existing_sessions(self):
        first, second = self.login(), self.login()
        self.user.invalidate_sessions()
        for client in (first, second):
            self.assertEqual(client.get(ME).status_code, 401)
        self.assertEqual(self.login().get(ME).status_code, 200)  # đăng nhập lại được

    def test_unlock_does_not_revive_old_session(self):
        """UC06.4 A1.3: mở khóa phải đăng nhập lại — kịch bản khóa đúng như service sẽ làm."""
        client = self.login()
        old_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.user.invalidate_sessions()
        self.assertEqual(client.get(ME).status_code, 401)
        User.objects.filter(pk=self.user.pk).update(is_active=True)
        replay = Client()
        replay.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
        self.assertEqual(replay.get(ME).status_code, 401)

    def test_without_version_bump_unlock_would_revive(self):
        """Đối chứng: chỉ đổi is_active (cách cũ) thì phiên cũ sống lại — lý do cần session_version."""
        client = self.login()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(client.get(ME).status_code, 401)
        User.objects.filter(pk=self.user.pk).update(is_active=True)
        self.assertEqual(client.get(ME).status_code, 200)

    def test_self_password_change_keeps_current_session(self):
        client = self.login()
        response = client.post(reverse("me-password"), {
            "current_password": PASSWORD, "new_password": "MatKhauMoi#2026", "new_password_confirm": "MatKhauMoi#2026",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(client.get(ME).status_code, 200)

    @override_settings(SECRET_KEY="khoa-moi-" + "x" * 50, SECRET_KEY_FALLBACKS=[settings.SECRET_KEY])
    def test_fallback_hash_also_respects_session_version(self):
        old = list(self.user.get_session_auth_fallback_hash())
        self.assertEqual(len(old), 1)
        self.user.invalidate_sessions()
        self.assertNotEqual(list(self.user.get_session_auth_fallback_hash()), old)

    def test_session_version_never_in_api(self):
        client = self.login()
        self.assertNotIn("session_version", client.get(ME).json())

    def test_invalidate_is_atomic_increment(self):
        stale = User.objects.get(pk=self.user.pk)
        self.user.invalidate_sessions()
        stale.invalidate_sessions()  # bản cũ trong bộ nhớ vẫn cộng đúng, không ghi đè về 1
        self.assertEqual(User.objects.get(pk=self.user.pk).session_version, 2)


class AccountEventTests(TestCase):
    def setUp(self):
        self.account = make_user("shop_a", "0900000001", UserRole.SHOP)
        self.actor = make_user("nv_a", "0900000002", UserRole.ADMIN)

    def test_event_fields_and_order(self):
        AccountEvent.objects.create(account=self.account, actor=self.actor, action=AccountAction.CREATED)
        AccountEvent.objects.create(account=self.account, actor=self.actor, action=AccountAction.LOCKED,
                                    reason="Nghỉ việc")
        events = list(self.account.account_events.all())
        self.assertEqual([e.action for e in events], [AccountAction.LOCKED, AccountAction.CREATED])
        self.assertEqual(events[0].reason, "Nghỉ việc")
        self.assertEqual(events[1].changes, {})

    def test_account_with_history_cannot_be_hard_deleted(self):
        AccountEvent.objects.create(account=self.account, actor=self.actor, action=AccountAction.CREATED)
        with self.assertRaises(ProtectedError):
            self.account.delete()
        with self.assertRaises(ProtectedError):
            self.actor.delete()

    def test_system_event_without_actor(self):
        event = AccountEvent.objects.create(account=self.account, action=AccountAction.PASSWORD_RESET)
        self.assertIsNone(event.actor)


class AccountEventAdminTests(TestCase):
    def test_read_only_in_django_admin(self):
        root = User.objects.create_superuser(username="root", password=PASSWORD, full_name="Root", phone="0900000099")
        event = AccountEvent.objects.create(account=root, action=AccountAction.CREATED)
        self.client.force_login(root)
        self.assertEqual(self.client.get(reverse("admin:accounts_accountevent_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:accounts_accountevent_add")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:accounts_accountevent_delete", args=[event.pk])).status_code, 403)
