import importlib

from django.apps import apps as django_apps
from django.db import models
from django.test import TestCase
from django.urls import reverse

from apps.accounts.constants import UserRole
from apps.core.choices import CHOICE_GROUPS
from apps.core.errors import ErrorCode
from apps.dispatch.constants import MAX_DELIVERY_ATTEMPTS, TERMINAL_TASK_STATUSES, TaskStatus
from apps.shipments.constants import COD_MAX_VND, TERMINAL_SHIPMENT_STATUSES, ShipmentStatus

# Enum không cần gửi frontend (mã lỗi đã nằm trong mỗi response lỗi).
NOT_EXPOSED = {ErrorCode}

EXPECTED_GROUPS = {
    "user_roles", "account_actions", "shipment_statuses", "shipment_actions", "holder_types",
    "task_types", "task_statuses", "task_actions", "notification_kinds", "pickup_fail_reasons", "handover_kinds",
    "delivery_fail_reasons",
    "limits", "hub",  # hub: spec 008 D6 (không phải enum)
}


class ChoicesEndpointTests(TestCase):
    url = reverse("meta-choices")

    def setUp(self):
        self.response = self.client.get(self.url)
        self.data = self.response.json()

    def test_public_without_login(self):
        self.assertEqual(self.response.status_code, 200)

    def test_has_all_groups(self):
        self.assertEqual(set(self.data), EXPECTED_GROUPS)

    def test_values_and_labels_match_enums_in_order(self):
        for name, (enum, _) in CHOICE_GROUPS.items():
            with self.subTest(group=name):
                self.assertEqual([i["value"] for i in self.data[name]], list(enum.values))
                self.assertEqual([i["label"] for i in self.data[name]], [str(x) for x in enum.labels])

    def test_vietnamese_labels(self):
        statuses = {i["value"]: i["label"] for i in self.data["shipment_statuses"]}
        self.assertEqual(statuses["PENDING_APPROVAL"], "Chờ xác nhận")
        self.assertEqual(statuses["AWAITING_SHOP_PICKUP"], "Chờ Shop đến lấy")
        self.assertIn("Chờ xác nhận", self.response.content.decode("utf-8"))  # không bị escape \uXXXX hỏng

    def test_terminal_flags(self):
        for name, enum, terminal in (
            ("shipment_statuses", ShipmentStatus, TERMINAL_SHIPMENT_STATUSES),
            ("task_statuses", TaskStatus, TERMINAL_TASK_STATUSES),
        ):
            with self.subTest(group=name):
                flagged = {i["value"] for i in self.data[name] if i["terminal"]}
                self.assertEqual(flagged, set(terminal))

    def test_terminal_only_on_status_groups(self):
        self.assertNotIn("terminal", self.data["user_roles"][0])

    def test_limits(self):
        self.assertEqual(self.data["limits"], {
            "max_delivery_attempts": MAX_DELIVERY_ATTEMPTS, "cod_max_vnd": COD_MAX_VND,
            "package_count_min": 1, "package_count_max": 99, "weight_grams_max": 100_000,
            "search_query_max_length": 100, "cancel_reason_max_length": 500, "reject_reason_max_length": 500,
            "task_note_max_length": 500, "handover_note_max_length": 500, "handover_receiver_name_max_length": 100,
            "location_ping_max_age_seconds": 120, "location_ping_max_future_seconds": 60,
            "location_ping_min_interval_seconds": 15, "location_ping_max_accuracy_m": 1000,
            "location_stale_seconds": 300, "location_poll_interval_seconds": 15, "location_retention_days": 30,
        })

    def test_same_for_logged_in_user(self):
        from apps.accounts.models import User

        user = User.objects.create_user(
            username="s", password="Matkhau@123", full_name="S", phone="0900000001", role=UserRole.SHIPPER
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).json(), self.data)

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)


class ChoicesRegistryTests(TestCase):
    def test_every_textchoices_in_constants_is_exposed(self):
        """Thêm enum vào constants.py mà quên đăng ký CHOICE_GROUPS thì test này báo."""
        registered = {enum for enum, _ in CHOICE_GROUPS.values()}
        found = set()
        for config in django_apps.get_app_configs():
            if not config.name.startswith("apps."):
                continue
            for module_name in ("constants", "errors"):
                try:
                    module = importlib.import_module(f"{config.name}.{module_name}")
                except ModuleNotFoundError:
                    continue
                for obj in vars(module).values():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, models.TextChoices)
                        and obj is not models.TextChoices
                        and obj.__module__ == module.__name__
                    ):
                        found.add(obj)
        self.assertTrue(found)
        missing = found - registered - NOT_EXPOSED
        self.assertEqual(missing, set(), f"Enum chưa đăng ký trong CHOICE_GROUPS: {missing}")
