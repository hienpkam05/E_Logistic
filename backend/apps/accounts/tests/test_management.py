"""Spec 003 Phase 2: danh sách, chi tiết, tạo, sửa tài khoản."""
import logging
import string
from unittest import mock

from django.core.cache import cache
from django.db import IntegrityError, connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts import services
from apps.accounts.constants import TEMP_PASSWORD_ALPHABET, TEMP_PASSWORD_LENGTH, AccountAction, UserRole
from apps.accounts.models import AccountEvent, User
from apps.core.errors import ErrorCode

PASSWORD = "Matkhau@12345"
LIST = reverse("account-list")
MANAGED_FIELDS = {"id", "username", "full_name", "phone", "address", "role", "is_active",
                  "must_change_password", "last_login", "date_joined", "updated_at"}
SENSITIVE = {"password", "session_version", "is_staff", "is_superuser", "groups", "user_permissions"}


def detail(pk):
    return reverse("account-detail", args=[pk])


def make_user(username, phone, role, **extra):
    return User.objects.create_user(username=username, password=PASSWORD, full_name=f"Tên {username}",
                                    phone=phone, role=role, **extra)


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user("nv_a", "0900000001", UserRole.ADMIN)
        self.admin2 = make_user("nv_b", "0900000002", UserRole.ADMIN)
        self.shop = make_user("shop_hoa", "0900000003", UserRole.SHOP, address="Hoàn Kiếm")
        self.shipper = make_user("shipper_long", "0900000004", UserRole.SHIPPER)
        self.locked = make_user("shipper_nghi", "0911111111", UserRole.SHIPPER, is_active=False)
        self.client.force_login(self.admin)

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        body = response.json()["error"]
        self.assertEqual(body["code"], code)
        return body

    def create(self, **data):
        payload = {"username": "shipper_moi", "full_name": "Shipper Mới", "phone": "0922222222",
                   "address": "", "role": UserRole.SHIPPER, **data}
        return self.client.post(LIST, payload, content_type="application/json")

    def patch(self, pk, client=None, **data):
        if "updated_at" not in data:
            data["updated_at"] = self.client.get(detail(pk)).json()["updated_at"]
        return (client or self.client).patch(detail(pk), data, content_type="application/json")


class PermissionTests(Base):
    def test_only_admin_role(self):
        for user in (self.shop, self.shipper):
            client = Client()
            client.force_login(user)
            for response in (client.get(LIST), client.get(detail(self.shop.pk)),
                             client.post(LIST, {}, content_type="application/json"),
                             client.patch(detail(self.shop.pk), {}, content_type="application/json")):
                with self.subTest(role=user.role, url=response.request["PATH_INFO"]):
                    self.assert_error(response, 403, ErrorCode.PERMISSION_DENIED)

    def test_anonymous_401(self):
        self.client.logout()
        self.assert_error(self.client.get(LIST), 401, ErrorCode.NOT_AUTHENTICATED)

    def test_admin_with_temp_password_blocked(self):
        User.objects.filter(pk=self.admin.pk).update(must_change_password=True)
        self.assert_error(self.client.get(LIST), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)

    def test_no_delete_endpoint(self):
        self.assert_error(self.client.delete(detail(self.shop.pk)), 405, ErrorCode.REQUEST_ERROR)
        self.assertTrue(User.objects.filter(pk=self.shop.pk).exists())


class ListTests(Base):
    def usernames(self, **params):
        return [u["username"] for u in self.client.get(LIST, params).json()["results"]]

    def test_fields_and_no_sensitive_data(self):
        body = self.client.get(LIST).json()
        self.assertEqual(body["count"], 5)
        for item in body["results"]:
            self.assertEqual(set(item), MANAGED_FIELDS)
            self.assertFalse(SENSITIVE & set(item))
        self.assertNotIn("pbkdf2", str(body))

    def test_sorted_by_role_then_username(self):
        self.assertEqual(self.usernames(), ["nv_a", "nv_b", "shipper_long", "shipper_nghi", "shop_hoa"])

    def test_filters(self):
        self.assertEqual(self.usernames(role="SHIPPER"), ["shipper_long", "shipper_nghi"])
        self.assertEqual(self.usernames(role="SHIPPER", is_active="false"), ["shipper_nghi"])
        self.assertEqual(self.usernames(is_active="true", role="SHOP"), ["shop_hoa"])

    def test_search_username_name_phone_case_insensitive(self):
        self.assertEqual(self.usernames(q="HOA"), ["shop_hoa"])
        self.assertEqual(self.usernames(q="Tên shipper_l"), ["shipper_long"])
        self.assertEqual(self.usernames(q="0911"), ["shipper_nghi"])
        self.assertEqual(self.usernames(q="   "), self.usernames())  # chỉ khoảng trắng = không lọc
        self.assertEqual(self.usernames(q="khong-co"), [])

    def test_invalid_filters(self):
        for params, field in (({"role": "KHACH"}, "role"), ({"is_active": "co-le"}, "is_active")):
            with self.subTest(params=params):
                err = self.assert_error(self.client.get(LIST, params), 400, ErrorCode.VALIDATION_ERROR)
                self.assertIn(field, err["fields"])

    def test_pagination_and_query_count_constant(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(LIST).status_code, 200)
            return len(ctx)

        few = count()
        for i in range(30):
            make_user(f"shop_{i:02d}", f"093000{i:04d}", UserRole.SHOP)
        self.assertEqual(count(), few)
        body = self.client.get(LIST, {"page": 2}).json()
        self.assertEqual((body["count"], len(body["results"])), (35, 15))

    def test_detail(self):
        body = self.client.get(detail(self.shop.pk)).json()
        self.assertEqual(set(body), MANAGED_FIELDS)
        self.assertEqual(body["address"], "Hoàn Kiếm")
        self.assert_error(self.client.get(detail(999999)), 404, ErrorCode.NOT_FOUND)

    def test_can_view_self(self):
        self.assertEqual(self.client.get(detail(self.admin.pk)).status_code, 200)


class TempPasswordTests(TestCase):
    def test_shape_and_validators(self):
        user = User(username="shipper_moi", full_name="Shipper Mới", phone="0922222222", role=UserRole.SHIPPER)
        seen = set()
        for _ in range(50):
            pw = services.generate_temp_password(user)
            seen.add(pw)
            self.assertEqual(len(pw), TEMP_PASSWORD_LENGTH)
            self.assertTrue(set(pw) <= set(TEMP_PASSWORD_ALPHABET))
            self.assertTrue(any(c in string.ascii_uppercase for c in pw))
            self.assertTrue(any(c in string.ascii_lowercase for c in pw))
            self.assertTrue(any(c in string.digits for c in pw))
        self.assertEqual(len(seen), 50)  # ngẫu nhiên, không lặp
        self.assertFalse(set("0O1lI") & set(TEMP_PASSWORD_ALPHABET))


class CreateTests(Base):
    def test_create_returns_temp_password_once(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(set(body), {"user", "temp_password"})
        self.assertEqual(set(body["user"]), MANAGED_FIELDS)
        self.assertTrue(body["user"]["must_change_password"])
        self.assertTrue(body["user"]["is_active"])
        user = User.objects.get(username="shipper_moi")
        self.assertEqual(user.role, UserRole.SHIPPER)
        self.assertTrue(user.check_password(body["temp_password"]))
        # Mật khẩu tạm không lấy lại được ở bất kỳ API nào khác
        self.assertNotIn(body["temp_password"], self.client.get(detail(user.pk)).content.decode())
        self.assertNotIn(body["temp_password"], self.client.get(LIST).content.decode())

    def test_new_account_must_change_password_on_first_login(self):
        temp = self.create().json()["temp_password"]
        client = Client()
        login = client.post(reverse("auth-login"), {"username": "shipper_moi", "password": temp},
                            content_type="application/json")
        self.assertTrue(login.json()["must_change_password"])
        self.assert_error(client.get(reverse("notification-list")), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)

    def test_event_recorded_with_actor_without_password(self):
        temp = self.create().json()["temp_password"]
        event = AccountEvent.objects.get(account__username="shipper_moi")
        self.assertEqual((event.action, event.actor), (AccountAction.CREATED, self.admin))
        self.assertNotIn(temp, str(event.changes) + event.reason)

    def test_each_role(self):
        for i, role in enumerate(UserRole.values):
            with self.subTest(role=role):
                response = self.create(username=f"moi_{i}", phone=f"094000000{i}", role=role)
                self.assertEqual(response.json()["user"]["role"], role)

    def test_password_field_in_request_ignored(self):
        response = self.create(password="DoNhanVienDat123", is_active=False, is_superuser=True)
        user = User.objects.get(username="shipper_moi")
        self.assertFalse(user.check_password("DoNhanVienDat123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(response.json()["temp_password"]))

    def test_invalid_input_creates_nothing(self):
        before = User.objects.count()
        cases = (
            ({"username": "shop_hoa"}, "username", "Tên đăng nhập đã được sử dụng."),
            ({"username": "SHOP_HOA"}, "username", "Tên đăng nhập đã được sử dụng."),  # khác hoa thường
            ({"phone": "0900000003"}, "phone", "Số điện thoại đã được sử dụng."),
            ({"username": "ab"}, "username", None),
            ({"username": "tên có dấu"}, "username", None),
            ({"phone": "123"}, "phone", None),
            ({"full_name": ""}, "full_name", None),
            ({"role": "KHACH"}, "role", None),
        )
        for data, field, message in cases:
            with self.subTest(data=data):
                err = self.assert_error(self.create(**data), 400, ErrorCode.VALIDATION_ERROR)
                self.assertIn(field, err["fields"])
                if message:
                    self.assertEqual(err["fields"][field], [message])
        self.assertEqual(User.objects.count(), before)
        self.assertFalse(AccountEvent.objects.exists())

    def test_race_integrity_error_becomes_field_error(self):
        """Hai request cùng qua serializer; người kia lưu trước nên DB từ chối request này."""
        from apps.core.errors import BusinessError

        make_user("trung_cung_luc", "0922222222", UserRole.SHOP)  # người khác vừa lấy SĐT
        data = {"username": "khac_han", "full_name": "Khác hẳn", "phone": "0922222222", "address": "",
                "role": UserRole.SHIPPER}
        with mock.patch.object(User.objects, "create_user", side_effect=IntegrityError("dup")):
            with self.assertRaises(BusinessError) as ctx:
                services.create_account(self.admin, data)
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(set(ctx.exception.fields), {"phone"})
        self.assertFalse(User.objects.filter(username="khac_han").exists())
        self.assertFalse(AccountEvent.objects.exists())

    def test_temp_password_never_logged(self):
        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger("kiem_tra").debug("bắt đầu")
            temp = self.create().json()["temp_password"]
        self.assertNotIn(temp, "\n".join(logs.output))


class UpdateTests(Base):
    def test_update_fields_and_event(self):
        response = self.patch(self.shop.pk, phone="0955555555", address="Ba Đình")
        self.assertEqual(response.status_code, 200, response.content)
        self.shop.refresh_from_db()
        self.assertEqual((self.shop.phone, self.shop.address), ("0955555555", "Ba Đình"))
        event = AccountEvent.objects.get(account=self.shop)
        self.assertEqual(event.action, AccountAction.UPDATED)
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.changes, {"phone": {"from": "0900000003", "to": "0955555555"},
                                         "address": {"from": "Hoàn Kiếm", "to": "Ba Đình"}})

    def test_protected_fields_ignored(self):
        self.patch(self.shop.pk, role="ADMIN", username="hacker", is_active=False, must_change_password=True,
                   full_name="Tên mới")
        self.shop.refresh_from_db()
        self.assertEqual((self.shop.role, self.shop.username, self.shop.is_active, self.shop.must_change_password),
                         (UserRole.SHOP, "shop_hoa", True, False))
        self.assertEqual(self.shop.full_name, "Tên mới")

    def test_no_change_no_event(self):
        self.assertEqual(self.patch(self.shop.pk, address="Hoàn Kiếm").status_code, 200)
        self.assertFalse(AccountEvent.objects.exists())

    def test_stale_version_conflict_saves_nothing(self):
        stale = self.client.get(detail(self.shop.pk)).json()["updated_at"]
        other = Client()
        other.force_login(self.admin2)
        self.assertEqual(self.patch(self.shop.pk, client=other, address="Người khác sửa").status_code, 200)
        err = self.assert_error(self.patch(self.shop.pk, updated_at=stale, address="Bản cũ"), 409, ErrorCode.CONFLICT)
        self.assertIn("người khác", err["message"])
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.address, "Người khác sửa")
        self.assertEqual(AccountEvent.objects.filter(account=self.shop).count(), 1)

    def test_missing_updated_at(self):
        response = self.client.patch(detail(self.shop.pk), {"address": "x"}, content_type="application/json")
        err = self.assert_error(response, 400, ErrorCode.VALIDATION_ERROR)
        self.assertIn("updated_at", err["fields"])

    def test_invalid_or_duplicate(self):
        for data, field in (({"phone": "0900000004"}, "phone"), ({"phone": "12"}, "phone"), ({"full_name": ""}, "full_name")):
            with self.subTest(data=data):
                err = self.assert_error(self.patch(self.shop.pk, **data), 400, ErrorCode.VALIDATION_ERROR)
                self.assertIn(field, err["fields"])
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.phone, "0900000003")

    def test_keep_own_phone_ok(self):
        self.assertEqual(self.patch(self.shop.pk, phone="0900000003", full_name="Đổi tên").status_code, 200)

    def test_cannot_edit_self(self):
        err = self.assert_error(self.patch(self.admin.pk, full_name="Tự sửa"), 403, ErrorCode.PERMISSION_DENIED)
        self.assertIn("Thông tin cá nhân", err["message"])

    def test_can_edit_other_admin_and_locked_account(self):
        self.assertEqual(self.patch(self.admin2.pk, full_name="NV B mới").status_code, 200)
        self.assertEqual(self.patch(self.locked.pk, address="Đống Đa").status_code, 200)

    def test_not_found(self):
        response = self.client.patch(detail(999999), {"updated_at": "2026-01-01T00:00:00Z"},
                                     content_type="application/json")
        self.assert_error(response, 404, ErrorCode.NOT_FOUND)
