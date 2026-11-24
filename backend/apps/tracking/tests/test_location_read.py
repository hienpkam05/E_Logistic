"""UC03.3: chỉ điểm task mở hiện tại, không lộ GPS đơn/task khác."""
from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from apps.accounts.services import lock_account
from apps.dispatch import services as dispatch
from apps.dispatch.constants import TaskStatus, TaskType
from apps.dispatch.models import Task, TaskResult
from apps.dispatch.tests.test_staff_swap import HUB
from apps.notifications.models import Notification
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_user
from apps.tracking.models import LocationPing
from .test_location_ingest import prepare


@override_settings(HUB=HUB)
class LocationReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        prepare(cls)
        cls.foreign_shop = make_user("gps_foreign", "0900000088")

    def setUp(self):
        self.client.force_login(self.shop)
        self.url = reverse("shipment-location", args=[self.shipment.pk])

    def ping(self, *, task=None, seconds=0, **extra):
        task = task or self.task
        return LocationPing.objects.create(task=task, shipper=task.shipper, lat=21.028511, lng=105.804817,
            accuracy_m=12.345, recorded_at=self.now + timedelta(seconds=seconds), received_at=self.now, **extra)

    def get(self, url=None):
        with patch("apps.tracking.views.timezone.now", return_value=self.now):
            return self.client.get(url or self.url)

    def test_latest_point_numbers_timestamps_and_no_shipper_identity(self):
        self.ping(seconds=-20)
        latest = self.ping(seconds=-1)
        result = self.get()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"task": {"id": self.task.pk, "type": TaskType.DELIVERY}, "location": {
            "lat": 21.028511, "lng": 105.804817, "accuracy": 12.345,
            "recorded_at": result.json()["location"]["recorded_at"],
            "received_at": result.json()["location"]["received_at"], "stale": False}})
        location = result.json()["location"]
        self.assertEqual(parse_datetime(location["recorded_at"]), latest.recorded_at)
        self.assertEqual(parse_datetime(location["received_at"]), self.now)
        for field in ("lat", "lng", "accuracy"):
            self.assertIsInstance(location[field], (float, int))

    def test_latest_by_device_time_then_id_not_receive_order(self):
        newest = self.ping(seconds=-1)
        self.ping(seconds=-20)
        self.assertEqual(parse_datetime(self.get().json()["location"]["recorded_at"]), newest.recorded_at)
        tie = self.ping(seconds=-1)
        LocationPing.objects.filter(pk=tie.pk).update(lat=0, lng=0, accuracy_m=None)
        location = self.get().json()["location"]
        self.assertEqual((location["lat"], location["lng"], location["accuracy"]), (0, 0, None))

    def test_stale_uses_recorded_time_and_exact_boundary(self):
        for seconds, expected in ((-300, False), (-300.001, True), (60, False)):
            with self.subTest(seconds=seconds):
                LocationPing.objects.all().delete()
                self.ping(seconds=seconds)
                self.assertIs(self.get().json()["location"]["stale"], expected)

    def test_open_task_without_point(self):
        self.assertEqual(self.get().json(), {"task": {"id": self.task.pk, "type": TaskType.DELIVERY}, "location": None})

    def test_no_open_task_and_each_terminal_status_hides_old_point(self):
        self.ping()
        for status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.REPLACED):
            with self.subTest(status=status):
                Task.objects.filter(pk=self.task.pk).update(status=status, closed_at=self.now)
                self.assertEqual(self.get().json(), {"task": None, "location": None})
        LocationPing.objects.all().delete()
        Task.objects.filter(pk=self.task.pk).delete()
        self.assertEqual(self.get().json(), {"task": None, "location": None})

    def test_pending_handover_shows_old_owner_point_then_new_task_has_none(self):
        self.ping()
        dispatch.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Nghỉ", self.shipment.updated_at)
        self.assertEqual(self.get().json()["task"]["id"], self.task.pk)
        self.assertIsNotNone(self.get().json()["location"])
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        dispatch.confirm_swap_handover(self.admin, shipment.pk, "", shipment.updated_at)
        current = Task.objects.get(shipment=shipment, status=TaskStatus.ACTIVE)
        self.assertEqual(self.get().json(), {"task": {"id": current.pk, "type": TaskType.DELIVERY}, "location": None})
        self.ping(task=current)
        self.assertIsNotNone(self.get().json()["location"])
        self.assertEqual(LocationPing.objects.count(), 2)

    def test_admin_sees_foreign_shop_while_shop_gets_same_404_as_missing(self):
        self.ping()
        self.client.force_login(self.foreign_shop)
        foreign = self.get()
        missing = self.get(reverse("shipment-location", args=[self.shipment.pk + 1000]))
        self.assertEqual((foreign.status_code, foreign.json()), (404, missing.json()))
        self.assertEqual(missing.status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.get().status_code, 200)
        self.assertIsNotNone(self.get().json()["location"])

    def test_anonymous_shipper_locked_and_temp_password(self):
        self.client.logout()
        self.assertEqual(self.get().status_code, 401)
        self.client.force_login(self.shipper)
        self.assertEqual(self.get().status_code, 403)
        self.shop.must_change_password = True
        self.shop.save(update_fields=["must_change_password"])
        self.client.force_login(self.shop)
        self.assertEqual(self.get().status_code, 403)
        self.shop.must_change_password = False
        self.shop.save(update_fields=["must_change_password"])
        lock_account(self.admin, self.shop.pk, "Thử")
        self.assertEqual(self.get().status_code, 401)

    def test_read_has_no_side_effects(self):
        self.ping()
        models = (Task, Shipment, ShipmentEvent, TaskResult, Notification, LocationPing)
        before = [list(model.objects.order_by("pk").values()) for model in models]
        self.assertEqual(self.get().status_code, 200)
        self.assertEqual([list(model.objects.order_by("pk").values()) for model in models], before)

    def test_query_count_constant_when_more_points_exist(self):
        self.ping()
        with CaptureQueriesContext(connection) as small:
            self.assertEqual(self.get().status_code, 200)
        LocationPing.objects.bulk_create([LocationPing(task=self.task, shipper=self.shipper, lat=0, lng=0,
            recorded_at=self.now - timedelta(seconds=i), received_at=self.now) for i in range(1000)])
        with CaptureQueriesContext(connection) as large:
            self.assertEqual(self.get().status_code, 200)
        self.assertEqual(len(small), len(large))
        self.assertLessEqual(len(large), 6)  # session/user auth + scoped shipment + one task/point query.

    def test_only_current_task_points_and_all_open_task_types(self):
        for task_type in (TaskType.PICKUP, TaskType.RETURN):
            with self.subTest(task_type=task_type):
                Task.objects.filter(pk=self.task.pk).update(type=task_type, attempt_no=None)
                self.assertEqual(self.get().json()["task"]["type"], task_type)
