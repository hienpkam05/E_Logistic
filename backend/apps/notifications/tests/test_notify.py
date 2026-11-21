from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.notifications.constants import NotificationKind
from apps.notifications.models import Notification
from apps.notifications.services import notify


def make_user(n, role=UserRole.SHOP):
    return User.objects.create_user(
        username=f"user{n}", password="Matkhau@123", full_name=f"User {n}", phone=f"09000000{n:02d}", role=role
    )


class NotifyTests(TestCase):
    def setUp(self):
        self.shop, self.admin = make_user(1), make_user(2, UserRole.ADMIN)

    def test_creates_one_per_recipient(self):
        created = notify([self.shop, self.admin], NotificationKind.REQUEST_APPROVED, "Yêu cầu đã duyệt",
                         payload={"shipment_id": 7})
        self.assertEqual(len(created), 2)
        self.assertEqual(Notification.objects.count(), 2)
        note = self.shop.notifications.get()
        self.assertEqual(note.kind, NotificationKind.REQUEST_APPROVED)
        self.assertEqual(note.payload, {"shipment_id": 7})
        self.assertFalse(note.is_read)

    def test_single_recipient_and_dedupe(self):
        self.assertEqual(len(notify(self.shop, NotificationKind.DELIVERED, "Đã giao")), 1)
        self.assertEqual(len(notify([self.shop, self.shop, None], NotificationKind.DELIVERED, "Đã giao")), 1)

    def test_no_recipients_creates_nothing(self):
        self.assertEqual(notify([], NotificationKind.DELIVERED, "x"), [])

    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValueError):
            notify(self.shop, "KHONG_CO", "x")
        self.assertFalse(Notification.objects.exists())

    def test_payload_not_shared_between_rows(self):
        payload = {"shipment_id": 1}
        a, b = notify([self.shop, self.admin], NotificationKind.DELIVERED, "x", payload=payload)
        a.payload["x"] = 1
        self.assertNotIn("x", b.payload)
        self.assertNotIn("x", payload)

    def test_rolled_back_with_business_transaction(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                notify(self.shop, NotificationKind.DELIVERED, "Đã giao")
                raise RuntimeError("nghiệp vụ lỗi sau khi tạo thông báo")
        self.assertFalse(Notification.objects.exists())

    def test_newest_first(self):
        notify(self.shop, NotificationKind.PICKED_UP, "1")
        notify(self.shop, NotificationKind.DELIVERED, "2")
        self.assertEqual([n.title for n in self.shop.notifications.all()], ["2", "1"])


class NotifyOutsideTransactionTests(TransactionTestCase):
    def test_must_be_called_inside_atomic(self):
        shop = make_user(1)
        with self.assertRaises(RuntimeError):
            notify(shop, NotificationKind.DELIVERED, "x")
        self.assertFalse(Notification.objects.exists())


class NotificationAdminTests(TestCase):
    def setUp(self):
        root = User.objects.create_superuser(username="root", password="Matkhau@123", full_name="Root",
                                             phone="0900000099")
        self.client.force_login(root)
        self.note = notify(root, NotificationKind.TASK_ASSIGNED, "Nhiệm vụ mới")[0]

    def test_read_only(self):
        self.assertEqual(self.client.get(reverse("admin:notifications_notification_changelist")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("admin:notifications_notification_change", args=[self.note.pk])).status_code, 200
        )
        self.assertEqual(self.client.get(reverse("admin:notifications_notification_add")).status_code, 403)
        self.client.post(reverse("admin:notifications_notification_change", args=[self.note.pk]), {"title": "sửa"})
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Nhiệm vụ mới")
