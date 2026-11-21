from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.accounts.permissions import HasRole


def make_user(username="shop_a", phone="0900000001", role=UserRole.SHOP, **extra):
    return User.objects.create_user(
        username=username, password="Matkhau@123", full_name="Shop A", phone=phone, role=role, **extra
    )


class UserModelTests(TestCase):
    def test_create_user_requires_role(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(username="x", password="Matkhau@123", full_name="X", phone="0900000009")

    def test_create_user_ok_and_password_hashed(self):
        user = make_user()
        self.assertEqual(user.role, UserRole.SHOP)
        self.assertTrue(user.is_shop)
        self.assertFalse(user.is_admin_role or user.is_shipper)
        self.assertNotEqual(user.password, "Matkhau@123")
        self.assertTrue(user.check_password("Matkhau@123"))
        self.assertFalse(user.must_change_password)

    def test_superuser_gets_admin_role(self):
        user = User.objects.create_superuser(
            username="root", password="Matkhau@123", full_name="Quản trị", phone="0900000002"
        )
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertTrue(user.is_staff and user.is_superuser)

    def test_superuser_with_other_role_rejected(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                username="root", password="Matkhau@123", full_name="X", phone="0900000003", role=UserRole.SHOP
            )

    def test_no_first_last_name(self):
        field_names = {f.name for f in User._meta.get_fields()}
        self.assertNotIn("first_name", field_names)
        self.assertNotIn("last_name", field_names)
        self.assertEqual(make_user().get_full_name(), "Shop A")

    def test_invalid_role_rejected_by_db(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(username="bad", full_name="X", phone="0900000004", role="KHACH")

    def test_duplicate_phone_rejected_by_db(self):
        make_user()
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_user(username="shop_b")

    def test_bad_phone_format_rejected(self):
        for phone in ("123", "1900000000", "09000000ab"):
            with self.subTest(phone=phone):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    User.objects.create(username=f"u{phone}", full_name="X", phone=phone, role=UserRole.SHOP)
                with self.assertRaises(ValidationError):
                    User(username="v", full_name="X", phone=phone, role=UserRole.SHOP).full_clean(
                        exclude=["password"]
                    )


class HasRolePermissionTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.admin_only = HasRole.of(UserRole.ADMIN)()

    def check(self, user, permission=None):
        self.request.user = user
        return (permission or self.admin_only).has_permission(self.request, None)

    def test_allows_matching_role(self):
        self.assertTrue(self.check(make_user(role=UserRole.ADMIN)))

    def test_denies_other_role(self):
        self.assertFalse(self.check(make_user(role=UserRole.SHOP)))

    def test_denies_anonymous(self):
        self.assertFalse(self.check(AnonymousUser()))

    def test_denies_locked_account(self):
        self.assertFalse(self.check(make_user(role=UserRole.ADMIN, is_active=False)))

    def test_multiple_roles(self):
        perm = HasRole.of(UserRole.SHOP, UserRole.ADMIN)()
        self.assertTrue(self.check(make_user(role=UserRole.SHOP), perm))
        self.assertFalse(self.check(make_user(username="sp", phone="0900000005", role=UserRole.SHIPPER), perm))

    def test_requires_at_least_one_role(self):
        with self.assertRaises(ValueError):
            HasRole.of()


class UserAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(
            username="root", password="Matkhau@123", full_name="Quản trị", phone="0900000002"
        )
        self.client.force_login(self.root)

    def test_admin_pages_render(self):
        for url in (
            reverse("admin:accounts_user_changelist"),
            reverse("admin:accounts_user_add"),
            reverse("admin:accounts_user_change", args=[self.root.pk]),
            reverse("admin:accounts_user_changelist") + "?q=090&role__exact=ADMIN",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_add_user(self):
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "username": "shipper_a",
                "full_name": "Shipper A",
                "phone": "0900000010",
                "role": UserRole.SHIPPER,
                "usable_password": "true",
                "password1": "Matkhau@123xyz",
                "password2": "Matkhau@123xyz",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context.get("errors"))
        self.assertTrue(User.objects.filter(username="shipper_a", role=UserRole.SHIPPER).exists())
