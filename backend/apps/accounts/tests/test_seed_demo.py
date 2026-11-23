import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.accounts.constants import UserRole
from apps.accounts.management.commands.seed_demo import DEMO_ACCOUNTS
from apps.accounts.models import User


def run(*args):
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_creates_one_account_per_role_and_superuser(self):
        run()
        self.assertEqual(User.objects.count(), len(DEMO_ACCOUNTS))
        self.assertEqual(set(User.objects.values_list("role", flat=True)), set(UserRole.values))
        superuser = User.objects.get(is_superuser=True)
        self.assertEqual(superuser.role, UserRole.ADMIN)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_passwords_random_and_usable(self):
        out = run()
        for spec in DEMO_ACCOUNTS:
            line = next(l for l in out.splitlines() if l.startswith(spec["username"]))
            password = line.split()[2]
            self.assertTrue(User.objects.get(username=spec["username"]).check_password(password))
        self.assertGreaterEqual(len(password), 12)

    def test_idempotent_without_reset(self):
        run()
        hashes = dict(User.objects.values_list("username", "password"))
        out = run()
        self.assertEqual(User.objects.count(), len(DEMO_ACCOUNTS))
        self.assertEqual(dict(User.objects.values_list("username", "password")), hashes)
        self.assertIn("đã tồn tại", out)

    def test_reset_changes_password(self):
        run()
        before = User.objects.get(username="demo_shop").password
        run("--reset")
        self.assertNotEqual(User.objects.get(username="demo_shop").password, before)

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.txt"
            out = run("--output", str(path))
            content = path.read_text(encoding="utf-8")
        self.assertIn("demo_shipper", content)
        self.assertNotIn("demo_shipper", out)  # mật khẩu không in ra màn hình khi ghi file


@override_settings(DEBUG=True)
class SeedDemoSpecialAccountsTests(TestCase):
    def test_temp_password_and_locked_accounts(self):
        run()
        self.assertTrue(User.objects.get(username="demo_mktam").must_change_password)
        self.assertFalse(User.objects.get(username="demo_khoa").is_active)
        self.assertTrue(User.objects.get(username="demo_shop").is_active)

    def test_reset_restores_demo_state(self):
        run()
        User.objects.filter(username="demo_mktam").update(must_change_password=False)
        User.objects.filter(username="demo_khoa").update(is_active=True)
        run("--reset")
        self.assertTrue(User.objects.get(username="demo_mktam").must_change_password)
        self.assertFalse(User.objects.get(username="demo_khoa").is_active)

    def test_rerun_with_output_keeps_known_passwords(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.txt"
            run("--output", str(path))
            first = path.read_text(encoding="utf-8")
            User.objects.filter(username="demo_khoa").delete()  # giả lập tài khoản mới thêm vào danh sách
            run("--output", str(path))
            second = path.read_text(encoding="utf-8")
        pw = lambda text, name: next(l.split()[2] for l in text.splitlines() if l.startswith(name))  # noqa: E731
        self.assertEqual(pw(first, "demo_shop"), pw(second, "demo_shop"))
        self.assertTrue(User.objects.get(username="demo_shop").check_password(pw(second, "demo_shop")))
        self.assertTrue(User.objects.get(username="demo_khoa").check_password(pw(second, "demo_khoa")))

    def test_demo_wards_clearly_fake_and_repeatable(self):
        from apps.accounts.management.commands.seed_demo import DEMO_WARDS
        from apps.shipments.models import Ward

        run("--wards")
        run("--wards")
        self.assertEqual(Ward.objects.count(), len(DEMO_WARDS))
        self.assertTrue(all(name.startswith("[Demo] ") for name in Ward.objects.values_list("name", flat=True)))

    def test_demo_wards_replaced_by_official_list(self):
        import tempfile
        from pathlib import Path
        from apps.shipments.models import Ward

        run("--wards")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wards.csv"
            path.write_text("code,name\n00001,Phường Thật\n", encoding="utf-8")
            call_command("load_wards", str(path), stdout=StringIO())
        self.assertEqual(list(Ward.objects.filter(is_active=True).values_list("name", flat=True)), ["Phường Thật"])

    def test_notifications_seed_is_repeatable(self):
        from apps.accounts.management.commands.seed_demo import DEMO_NOTIFICATION_COUNT
        from apps.notifications.models import Notification

        run("--notifications")
        run("--notifications")  # lần 2 xóa thông báo mẫu cũ rồi tạo lại, không nhân đôi
        self.assertEqual(Notification.objects.count(), sum(DEMO_NOTIFICATION_COUNT.values()))
        self.assertGreater(Notification.objects.filter(recipient__username="demo_shop").count(), 20)


@override_settings(DEBUG=True)
class SeedDemoFailureTests(TestCase):
    def test_no_credentials_file_when_db_fails(self):
        """Lỗi giữa chừng: DB rollback và KHÔNG ghi file mật khẩu."""
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.txt"
            with mock.patch.object(User.objects, "create_user", side_effect=RuntimeError("DB lỗi")):
                with self.assertRaises(RuntimeError):
                    run("--output", str(path))
            self.assertFalse(path.exists())
        self.assertFalse(User.objects.exists())


@override_settings(DEBUG=False)
class SeedDemoProductionGuardTests(TestCase):
    def test_refuses_when_debug_false(self):
        with self.assertRaises(CommandError):
            run()
        self.assertFalse(User.objects.exists())
