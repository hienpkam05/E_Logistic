import logging
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.core.errors import ErrorCode

PASSWORD = "Matkhau@12345"
NEW_PASSWORD = "MatKhauMoi#2026"
LOGIN, ME, PASSWORD_URL = reverse("auth-login"), reverse("me"), reverse("me-password")


def make_user(username, phone, role=UserRole.SHOP, **extra):
    return User.objects.create_user(
        username=username, password=PASSWORD, full_name="Shop Hoa An", phone=phone, role=role, **extra
    )


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("shop_a", "0900000001", address="1 Tràng Tiền")
        self.other = make_user("shop_b", "0900000002")
        self.client.force_login(self.user)

    def patch(self, data, client=None):
        return (client or self.client).patch(ME, data, content_type="application/json")

    def change(self, current=PASSWORD, new=NEW_PASSWORD, confirm=None, client=None):
        return (client or self.client).post(
            PASSWORD_URL,
            {"current_password": current, "new_password": new, "new_password_confirm": confirm or new},
            content_type="application/json",
        )

    def login_client(self, password=PASSWORD):
        client = Client()
        response = client.post(LOGIN, {"username": "shop_a", "password": password}, content_type="application/json")
        return client, response.status_code

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        body = response.json()["error"]
        self.assertEqual(body["code"], code)
        return body


class UpdateProfileTests(Base):
    def test_update_each_field(self):
        for field, value in (("full_name", "Shop Hoa An Mới"), ("phone", "0912345678"), ("address", "")):
            with self.subTest(field=field):
                response = self.patch({field: value})
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()[field], value)
                self.user.refresh_from_db()
                self.assertEqual(getattr(self.user, field), value)

    def test_protected_fields_ignored(self):
        response = self.patch({"role": "ADMIN", "is_active": False, "username": "hacker", "is_staff": True,
                               "email": "x@example.com", "must_change_password": True, "address": "Mới"})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual((self.user.role, self.user.is_active, self.user.username, self.user.is_staff,
                          self.user.email, self.user.must_change_password),
                         (UserRole.SHOP, True, "shop_a", False, "", False))
        self.assertEqual(self.user.address, "Mới")

    def test_invalid_input_saves_nothing(self):
        cases = (
            ({"phone": "0900000002"}, "phone"),        # trùng người khác
            ({"phone": "12345"}, "phone"),             # sai định dạng
            ({"full_name": ""}, "full_name"),          # rỗng
            ({"full_name": "   "}, "full_name"),       # chỉ khoảng trắng
        )
        for data, field in cases:
            with self.subTest(data=data):
                err = self.assert_error(self.patch({**data, "address": "Không được lưu"}), 400,
                                        ErrorCode.VALIDATION_ERROR)
                self.assertEqual(set(err["fields"]), {field})
                self.user.refresh_from_db()
                self.assertEqual(self.user.address, "1 Tràng Tiền")

    def test_duplicate_phone_message_vietnamese(self):
        err = self.assert_error(self.patch({"phone": "0900000002"}), 400, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(err["fields"]["phone"], ["Số điện thoại đã được sử dụng."])

    def test_keep_own_phone_is_not_duplicate(self):
        self.assertEqual(self.patch({"phone": "0900000001"}).status_code, 200)

    def test_race_on_phone_becomes_field_error(self):
        # Vượt qua kiểm tra trùng của serializer nhưng DB từ chối (hai người lưu cùng lúc).
        with mock.patch.object(User, "save", side_effect=IntegrityError("duplicate key")):
            err = self.assert_error(self.patch({"phone": "0911111111"}), 400, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(set(err["fields"]), {"phone"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "0900000001")

    def test_requires_login(self):
        self.client.logout()
        self.assert_error(self.patch({"address": "x"}), 401, ErrorCode.NOT_AUTHENTICATED)


class ChangePasswordTests(Base):
    def test_errors_keep_old_password(self):
        cases = (
            ({"current": "sai-mat-khau"}, "current_password"),
            ({"new": "123"}, "new_password"),                                   # yếu
            ({"new": "password"}, "new_password"),                              # phổ biến
            ({"new": PASSWORD}, "new_password"),                                # trùng cũ
            ({"confirm": "KhacNhau#2026"}, "new_password_confirm"),             # không khớp
        )
        for kwargs, field in cases:
            with self.subTest(**kwargs):
                err = self.assert_error(self.change(**kwargs), 400, ErrorCode.VALIDATION_ERROR)
                self.assertIn(field, err["fields"])
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(PASSWORD))

    def test_weak_password_messages_in_vietnamese(self):
        err = self.assert_error(self.change(new="Ab1"), 400, ErrorCode.VALIDATION_ERROR)
        messages = err["fields"]["new_password"]
        self.assertIn("Mật khẩu quá ngắn, cần ít nhất 8 ký tự.", messages)
        self.assertFalse([m for m in messages if "password" in m.lower()], messages)  # không còn câu tiếng Anh

    def test_success_keeps_current_session_and_kills_others(self):
        cache.clear()
        first, status1 = self.login_client()
        second, status2 = self.login_client()
        self.assertEqual((status1, status2), (200, 200))
        self.assertEqual(self.change(client=first).status_code, 204)
        self.assertEqual(first.get(ME).status_code, 200)                    # phiên đang dùng còn
        self.assert_error(second.get(ME), 401, ErrorCode.NOT_AUTHENTICATED)  # phiên khác mất
        cache.clear()
        self.assertEqual(self.login_client(NEW_PASSWORD)[1], 200)
        self.assertEqual(self.login_client(PASSWORD)[1], 400)

    def test_password_never_in_response_or_logs(self):
        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger("kiem_tra").debug("bắt đầu")  # để assertLogs luôn có ít nhất một dòng
            responses = [self.change(current="sai-mat-khau"), self.change()]
        for response in responses:
            body = response.content.decode()
            self.assertNotIn(NEW_PASSWORD, body)
            self.assertNotIn("sai-mat-khau", body)
        joined = "\n".join(logs.output)
        self.assertNotIn(NEW_PASSWORD, joined)
        self.assertNotIn(PASSWORD, joined)

    def test_rate_limited_per_account(self):
        rate = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["password_change"].split("/")[0])
        for _ in range(rate):
            self.change(current="sai")
        self.assert_error(self.change(), 429, ErrorCode.REQUEST_ERROR)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
        other = Client()
        other.force_login(self.other)  # tài khoản khác không bị ảnh hưởng
        self.assertEqual(self.change(client=other).status_code, 204)


class TemporaryPasswordFlowTests(Base):
    """Mật khẩu tạm (UC01.3 qua Nhân viên, spec 002 D5)."""

    def setUp(self):
        super().setUp()
        User.objects.filter(pk=self.user.pk).update(must_change_password=True)

    def test_blocked_until_password_changed(self):
        self.assertTrue(self.client.get(ME).json()["must_change_password"])
        self.assert_error(self.patch({"address": "x"}), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)
        self.assertEqual(self.change().status_code, 204)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertFalse(self.client.get(ME).json()["must_change_password"])
        self.assertEqual(self.patch({"address": "Đã đổi"}).status_code, 200)

    def test_failed_change_keeps_flag(self):
        self.change(current="sai")
        self.user.refresh_from_db()
        self.assertTrue(self.user.must_change_password)
