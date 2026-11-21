from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.core.errors import ErrorCode
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.notifications.services import notify

LIST = reverse("notification-list")
COUNT = reverse("notification-unread-count")
READ_ALL = reverse("notification-read-all")
FIELDS = {"id", "kind", "title", "body", "payload", "created_at", "read_at", "is_read"}


def read_url(pk):
    return reverse("notification-read", args=[pk])


def make_user(username, phone, role=UserRole.SHOP, **extra):
    return User.objects.create_user(username=username, password="Matkhau@12345", full_name=username,
                                    phone=phone, role=role, **extra)


class NotificationApiTests(TestCase):
    def setUp(self):
        self.me = make_user("shop_a", "0900000001")
        self.other = make_user("shop_b", "0900000002")
        self.mine = [notify(self.me, NotificationKind.REQUEST_APPROVED, f"Của tôi {i}",
                            payload={"shipment_id": i})[0] for i in range(3)]
        self.theirs = notify(self.other, NotificationKind.DELIVERED, "Của người khác")[0]
        self.client.force_login(self.me)

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)

    # --- Danh sách ---
    def test_list_only_mine_newest_first(self):
        body = self.client.get(LIST).json()
        self.assertEqual(body["count"], 3)
        self.assertEqual([n["title"] for n in body["results"]], ["Của tôi 2", "Của tôi 1", "Của tôi 0"])
        self.assertEqual(set(body["results"][0]), FIELDS)
        self.assertEqual(body["results"][0]["payload"], {"shipment_id": 2})
        self.assertNotIn("recipient", body["results"][0])

    def test_unread_filter(self):
        Notification.objects.filter(pk=self.mine[0].pk).update(read_at=timezone.now())
        self.assertEqual(self.client.get(LIST, {"unread": "true"}).json()["count"], 2)
        self.assertEqual(self.client.get(LIST, {"unread": "false"}).json()["count"], 1)
        self.assertEqual(self.client.get(LIST).json()["count"], 3)

    def test_invalid_unread_param(self):
        response = self.client.get(LIST, {"unread": "co-le"})
        self.assert_error(response, 400, ErrorCode.VALIDATION_ERROR)
        self.assertIn("unread", response.json()["error"]["fields"])

    def test_pagination(self):
        for i in range(25):
            notify(self.me, NotificationKind.TASK_ASSIGNED, f"thêm {i}")
        body = self.client.get(LIST).json()
        self.assertEqual((body["count"], len(body["results"])), (28, 20))
        self.assertEqual(len(self.client.get(LIST, {"page": 2}).json()["results"]), 8)
        self.assertEqual(len(self.client.get(LIST, {"page_size": 5}).json()["results"]), 5)

    def test_list_query_count_constant(self):
        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(LIST).status_code, 200)
            return len(ctx)

        few = count_queries()
        for i in range(30):
            notify(self.me, NotificationKind.TASK_ASSIGNED, f"thêm {i}")
        self.assertEqual(count_queries(), few)  # không N+1

    # --- Đếm ---
    def test_unread_count(self):
        self.assertEqual(self.client.get(COUNT).json(), {"count": 3})
        Notification.objects.filter(pk=self.mine[0].pk).update(read_at=timezone.now())
        self.assertEqual(self.client.get(COUNT).json(), {"count": 2})

    # --- Đánh dấu đã đọc ---
    def test_mark_read(self):
        response = self.client.post(read_url(self.mine[0].pk))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_read"])
        self.assertIsNotNone(response.json()["read_at"])
        self.assertEqual(self.client.get(COUNT).json(), {"count": 2})

    def test_mark_read_twice_keeps_first_time(self):
        first = timezone.now() - timedelta(days=1)
        Notification.objects.filter(pk=self.mine[0].pk).update(read_at=first)
        response = self.client.post(read_url(self.mine[0].pk))
        self.assertEqual(response.status_code, 200)
        self.mine[0].refresh_from_db()
        self.assertEqual(self.mine[0].read_at, first)

    def test_cannot_touch_others_notification(self):
        self.assert_error(self.client.post(read_url(self.theirs.pk)), 404, ErrorCode.NOT_FOUND)
        self.assert_error(self.client.post(read_url(999999)), 404, ErrorCode.NOT_FOUND)
        self.theirs.refresh_from_db()
        self.assertIsNone(self.theirs.read_at)

    def test_others_404_same_as_missing(self):
        a = self.client.post(read_url(self.theirs.pk)).json()
        b = self.client.post(read_url(999999)).json()
        self.assertEqual(a, b)

    def test_read_all(self):
        Notification.objects.filter(pk=self.mine[0].pk).update(read_at=timezone.now())
        self.assertEqual(self.client.post(READ_ALL).json(), {"updated": 2})
        self.assertEqual(self.client.post(READ_ALL).json(), {"updated": 0})
        self.assertEqual(self.client.get(COUNT).json(), {"count": 0})
        self.theirs.refresh_from_db()
        self.assertIsNone(self.theirs.read_at)

    def test_get_not_allowed_on_actions(self):
        self.assert_error(self.client.get(read_url(self.mine[0].pk)), 405, ErrorCode.REQUEST_ERROR)
        self.assert_error(self.client.get(READ_ALL), 405, ErrorCode.REQUEST_ERROR)

    # --- Quyền ---
    def test_requires_login(self):
        self.client.logout()
        for method, url in (("get", LIST), ("get", COUNT), ("post", read_url(self.mine[0].pk)), ("post", READ_ALL)):
            with self.subTest(url=url):
                self.assert_error(getattr(self.client, method)(url), 401, ErrorCode.NOT_AUTHENTICATED)

    def test_blocked_when_password_change_required(self):
        User.objects.filter(pk=self.me.pk).update(must_change_password=True)
        self.assert_error(self.client.get(LIST), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)
        self.assert_error(self.client.post(READ_ALL), 403, ErrorCode.PASSWORD_CHANGE_REQUIRED)

    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.me)
        self.assert_error(client.post(READ_ALL), 403, ErrorCode.PERMISSION_DENIED)
        token = client.get(reverse("auth-csrf")).cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(client.post(READ_ALL, HTTP_X_CSRFTOKEN=token).status_code, 200)
