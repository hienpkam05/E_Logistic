from django.test import TestCase, override_settings

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.core.errors import BusinessError, ErrorCode


def assert_error(test, response, status, code, fields=None):
    test.assertEqual(response.status_code, status, response.content)
    body = response.json()
    test.assertEqual(set(body), {"error"})
    test.assertEqual(set(body["error"]), {"code", "message", "fields"})
    test.assertEqual(body["error"]["code"], code)
    test.assertTrue(body["error"]["message"])
    if fields is not None:
        test.assertEqual(body["error"]["fields"], fields)
    return body["error"]


@override_settings(ROOT_URLCONF="apps.core.tests.error_urls")
class ExceptionHandlerTests(TestCase):
    def test_serializer_validation_error_has_fields(self):
        err = assert_error(self, self.client.post("/t/validation/", {}), 400, "VALIDATION_ERROR")
        self.assertIn("phone", err["fields"])

    def test_malformed_json_is_validation_error(self):
        response = self.client.post("/t/validation/", "{khong-phai-json", content_type="application/json")
        assert_error(self, response, 400, "VALIDATION_ERROR", fields={})

    def test_business_error_custom_message(self):
        err = assert_error(self, self.client.get("/t/business/"), 409, "INVALID_TRANSITION", fields={})
        self.assertEqual(err["message"], "Yêu cầu không còn ở trạng thái Chờ xác nhận.")

    def test_business_error_default_message(self):
        err = assert_error(self, self.client.get("/t/business-default/"), 409, "LIMIT_REACHED")
        self.assertEqual(err["message"], ErrorCode.LIMIT_REACHED.label)

    def test_django_validation_error(self):
        assert_error(
            self, self.client.get("/t/django-validation/"), 400, "VALIDATION_ERROR",
            fields={"cod_amount": ["COD không được âm."]},
        )

    def test_not_authenticated_is_401_not_403(self):
        assert_error(self, self.client.get("/t/auth/"), 401, "NOT_AUTHENTICATED")

    def test_wrong_role_is_403(self):
        shop = User.objects.create_user(
            username="shop", password="Matkhau@123", full_name="Shop", phone="0900000001", role=UserRole.SHOP
        )
        self.client.force_login(shop)
        assert_error(self, self.client.get("/t/admin-only/"), 403, "PERMISSION_DENIED")

    def test_http404_hides_detail(self):
        err = assert_error(self, self.client.get("/t/not-found/"), 404, "NOT_FOUND")
        self.assertNotIn("nội bộ", err["message"])

    def test_unexpected_error_is_500_without_leak(self):
        with self.assertLogs("apps.core.exception_handler", level="ERROR") as logs:
            response = self.client.get("/t/crash/")
        err = assert_error(self, response, 500, "SERVER_ERROR", fields={})
        self.assertNotIn("password", response.content.decode())
        self.assertIn("RuntimeError", "\n".join(logs.output))  # traceback vẫn có trong log
        self.assertEqual(err["message"], ErrorCode.SERVER_ERROR.label)

    def test_method_not_allowed_keeps_status(self):
        assert_error(self, self.client.get("/t/validation/"), 405, "REQUEST_ERROR")

    def test_business_error_rejects_unknown_code(self):
        with self.assertRaises(ValueError):
            BusinessError("KHONG_CO")


class ApiNotFoundTests(TestCase):
    def test_unknown_api_path_returns_json_404(self):
        # Đường dẫn chắc chắn không có route (/api/v1/shipments/123/ đã thành route thật ở spec 004).
        for url in ("/api/v1/khong-ton-tai/", "/api/v1/shipments/khong-co/", "/api/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                assert_error(self, response, 404, "NOT_FOUND", fields={})
                # UTF-8 thật, nhất quán với phản hồi DRF (không escape \uXXXX).
                self.assertIn(ErrorCode.NOT_FOUND.label, response.content.decode("utf-8"))

    def test_missing_trailing_slash_still_redirects(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/api/v1/health/")

    def test_health_unchanged(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "htt-express-api"})

    def test_non_api_path_not_affected(self):
        response = self.client.get("/khong-phai-api/")
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response.get("Content-Type"), "application/json")


@override_settings(ROOT_URLCONF="apps.core.tests.error_urls")
class PaginationTests(TestCase):
    def test_default_page_size_20(self):
        body = self.client.get("/t/numbers/").json()
        self.assertEqual(body["count"], 250)
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNone(body["previous"])
        self.assertIn("page=2", body["next"])

    def test_custom_page_size(self):
        body = self.client.get("/t/numbers/?page_size=50&page=2").json()
        self.assertEqual(body["results"][0], 51)
        self.assertEqual(len(body["results"]), 50)

    def test_page_size_capped_at_100(self):
        self.assertEqual(len(self.client.get("/t/numbers/?page_size=1000").json()["results"]), 100)

    def test_invalid_page_is_404_json(self):
        assert_error(self, self.client.get("/t/numbers/?page=999"), 404, "NOT_FOUND")
