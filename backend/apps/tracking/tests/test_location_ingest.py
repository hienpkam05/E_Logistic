"""UC03.5: GPS chỉ ghi cho đúng nhiệm vụ, không thay dữ liệu giao nhận."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.services import lock_account
from apps.core.errors import ErrorCode
from apps.core.tests.race import RaceMixin
from apps.dispatch import services as dispatch
from apps.dispatch.constants import TaskStatus
from apps.dispatch.models import Task, TaskResult
from apps.dispatch.tests.test_shipper_swap import delivery_fixture
from apps.dispatch.tests.test_staff_swap import HUB
from apps.notifications.models import Notification
from apps.shipments.models import Shipment, ShipmentEvent
from apps.tracking.models import LocationPing
from apps.tracking.services import record_location


def prepare(obj):
    delivery_fixture(obj)
    obj.now = timezone.now()
    Task.objects.filter(pk=obj.task.pk).update(assigned_at=obj.now - timedelta(minutes=10))
    obj.task.refresh_from_db()


def point(now, **extra):
    return {"lat": 21.028511123, "lng": 105.804817123, "accuracy": 12.3456,
            "recorded_at": now.isoformat(), **extra}


@override_settings(HUB=HUB)
class LocationIngestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        prepare(cls)

    def setUp(self):
        self.client.force_login(self.shipper)
        self.url = reverse("task-location-create", args=[self.task.pk])

    def post(self, payload=None, *, now=None, url=None):
        with patch("apps.tracking.services.timezone.now", return_value=now or self.now):
            return self.client.post(url or self.url, point(self.now) if payload is None else payload,
                                    content_type="application/json")

    def test_store_only_location_with_server_identity_and_rounded_precision(self):
        before = (list(Shipment.objects.values()), list(Task.objects.values()), ShipmentEvent.objects.count(),
                  Notification.objects.count(), TaskResult.objects.count())
        response = self.post()
        self.assertEqual((response.status_code, response.json()), (201, {"stored": True}))
        ping = LocationPing.objects.get()
        self.assertEqual((ping.task, ping.shipper, ping.lat, ping.lng, ping.accuracy_m, ping.recorded_at, ping.received_at),
                         (self.task, self.shipper, Decimal("21.028511"), Decimal("105.804817"), Decimal("12.346"), self.now, self.now))
        self.assertEqual(before, (list(Shipment.objects.values()), list(Task.objects.values()), ShipmentEvent.objects.count(),
                                 Notification.objects.count(), TaskResult.objects.count()))

    def test_authentication_role_and_temp_password(self):
        self.client.logout()
        self.assertEqual(self.post().status_code, 401)
        for user in (self.shop, self.admin):
            self.client.force_login(user)
            self.assertEqual(self.post({}).status_code, 403)
        self.shipper.must_change_password = True
        self.shipper.save(update_fields=["must_change_password"])
        self.client.force_login(self.shipper)
        self.assertEqual(self.post().json()["error"]["code"], ErrorCode.PASSWORD_CHANGE_REQUIRED)
        self.assertFalse(LocationPing.objects.exists())

    def test_locked_user_session_rejected(self):
        lock_account(self.admin, self.shipper.pk, "Thử khóa")
        self.assertEqual(self.post().status_code, 401)
        self.assertFalse(LocationPing.objects.exists())

    def test_foreign_task_and_missing_have_same_404_before_payload_validation(self):
        self.client.force_login(self.other)
        foreign = self.post({})
        missing = self.post({}, url=reverse("task-location-create", args=[self.task.pk + 1000]))
        self.assertEqual((foreign.status_code, foreign.json()), (404, missing.json()))
        self.assertEqual(missing.status_code, 404)
        self.assertFalse(LocationPing.objects.exists())

    def test_closed_statuses_rejected_before_invalid_payload(self):
        for status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.REPLACED):
            with self.subTest(status=status):
                Task.objects.filter(pk=self.task.pk).update(status=status, closed_at=self.now)
                response = self.post({})
                self.assertEqual((response.status_code, response.json()["error"]["code"]), (409, ErrorCode.INVALID_TRANSITION))
        self.assertFalse(LocationPing.objects.exists())

    def test_pending_handover_old_shipper_allowed_candidate_denied(self):
        dispatch.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Thử", self.shipment.updated_at)
        self.assertEqual(self.post().status_code, 201)
        self.client.force_login(self.other)
        self.assertEqual(self.post().status_code, 404)
        self.assertEqual(LocationPing.objects.count(), 1)

    def test_replaced_task_stops_and_new_task_accepts_its_owner(self):
        dispatch.swap_shipper(self.admin, self.shipment.pk, self.other.pk, "Thử", self.shipment.updated_at)
        self.assertEqual(self.post().status_code, 201)
        shipment = Shipment.objects.get(pk=self.shipment.pk)
        dispatch.confirm_swap_handover(self.admin, shipment.pk, "", shipment.updated_at)
        self.assertEqual(self.post().status_code, 409)
        new_task = Task.objects.get(shipment=shipment, status=TaskStatus.ACTIVE)
        self.client.force_login(self.other)
        when = timezone.now() + timedelta(seconds=1)
        self.assertEqual(self.post(point(when), now=when, url=reverse("task-location-create", args=[new_task.pk])).status_code, 201)
        self.assertEqual(LocationPing.objects.filter(task=new_task, shipper=self.other).count(), 1)

    def test_coordinate_accuracy_edges_and_nullable_accuracy(self):
        for lat, lng, accuracy in ((-90, -180, 0), (90, 180, 1000), (0, 0, None)):
            with self.subTest(lat=lat, lng=lng, accuracy=accuracy):
                self.assertEqual(self.post(point(self.now, lat=lat, lng=lng, accuracy=accuracy)).status_code, 201)
                LocationPing.objects.all().delete()
        data = point(self.now)
        del data["accuracy"]
        self.assertEqual(self.post(data).status_code, 201)
        self.assertIsNone(LocationPing.objects.get().accuracy_m)

    def test_invalid_numbers_and_outside_bounds_before_rounding(self):
        cases = {"lat": [None, True, [], "NaN", "Infinity", "-Infinity", "90.00000001", "-90.00000001"],
                 "lng": [False, {}, "NaN", "180.00000001", "-180.00000001"],
                 "accuracy": [True, "NaN", "Infinity", -0.001, "1000.00001"]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response = self.post(point(self.now, **{field: value}))
                    self.assertEqual(response.status_code, 400, response.content)
                    self.assertIn(field, response.json()["error"]["fields"])
        self.assertFalse(LocationPing.objects.exists())

    def test_required_unknown_fields_and_malformed_body(self):
        for field in ("lat", "lng", "recorded_at"):
            data = point(self.now)
            del data[field]
            self.assertEqual(self.post(data).status_code, 400)
        for field in ("shipper_id", "task", "received_at"):
            self.assertEqual(self.post(point(self.now, **{field: self.other.pk})).status_code, 400)
        self.assertEqual(self.post([]).status_code, 400)
        self.assertFalse(LocationPing.objects.exists())

    def test_timestamp_requires_timezone_and_valid_type(self):
        for value in (None, True, 123, "", "bad", "2026-11-23T08:00:00", "2026-99-99T08:00:00Z"):
            with self.subTest(value=value):
                self.assertEqual(self.post(point(self.now, recorded_at=value)).status_code, 400)
        offset = self.now.astimezone(timezone.get_fixed_timezone(420)).isoformat()
        self.assertEqual(self.post(point(self.now, recorded_at=offset)).status_code, 201)
        self.assertEqual(LocationPing.objects.get().recorded_at, self.now)

    def test_time_window_exact_boundaries_and_before_assignment(self):
        for seconds, expected in ((-120, 201), (-120.001, 400), (60, 201), (60.001, 400)):
            with self.subTest(seconds=seconds):
                self.assertEqual(self.post(point(self.now + timedelta(seconds=seconds))).status_code, expected)
                LocationPing.objects.all().delete()
        Task.objects.filter(pk=self.task.pk).update(assigned_at=self.now - timedelta(seconds=10))
        self.assertEqual(self.post(point(self.now - timedelta(seconds=11))).status_code, 400)
        self.assertEqual(self.post(point(self.now - timedelta(seconds=10))).status_code, 201)

    def test_server_receive_interval_boundary_and_no_extension_by_dropped_requests(self):
        self.assertEqual(self.post().status_code, 201)
        for elapsed, expected in ((1, 200), (14.999, 200), (15, 201)):
            now = self.now + timedelta(seconds=elapsed)
            response = self.post(point(now), now=now)
            self.assertEqual((response.status_code, response.json()), (expected, {"stored": expected == 201}))
        self.assertEqual(LocationPing.objects.count(), 2)

    def test_replay_and_out_of_order_do_not_refresh_recorded_or_received_time(self):
        self.post()
        for seconds in (0, -1):
            self.assertEqual(self.post(point(self.now + timedelta(seconds=seconds)), now=self.now + timedelta(seconds=16)).json(), {"stored": False})
        ping = LocationPing.objects.get()
        self.assertEqual((ping.recorded_at, ping.received_at), (self.now, self.now))

    def test_invalid_data_still_rejected_during_throttle(self):
        self.post()
        self.assertEqual(self.post(point(self.now, lat=100)).status_code, 400)
        self.assertEqual(self.post(point(self.now - timedelta(seconds=121))).status_code, 400)
        self.assertEqual(LocationPing.objects.count(), 1)

    def test_database_checks_reject_out_of_range(self):
        for changes in ({"lat": 91}, {"lng": -181}, {"accuracy_m": -1}, {"accuracy_m": 1001}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                LocationPing.objects.create(task=self.task, shipper=self.shipper, recorded_at=self.now,
                                            **{"lat": 0, "lng": 0, **changes})


@override_settings(HUB=HUB)
class LocationRaceTests(RaceMixin, TransactionTestCase):
    def setUp(self):
        prepare(self)

    def record(self):
        return record_location(self.shipper, self.task.pk, point(timezone.now()))

    def test_simultaneous_points_store_only_one(self):
        self.assertEqual(self.run_parallel(self.record, self.record), ["ok", "ok"])
        self.assertEqual(LocationPing.objects.count(), 1)

    def test_task_closed_before_ping_lock_rejects(self):
        result = self.race(lambda: dispatch.confirm_delivery(self.shipper, self.task.pk, self.shipment.cod_amount), self.record)
        self.assertEqual(result, ErrorCode.INVALID_TRANSITION)
        self.assertFalse(LocationPing.objects.exists())

    def test_user_locked_before_ping_lock_rejects(self):
        result = self.race(lambda: lock_account(self.admin, self.shipper.pk, "Thử"), self.record)
        self.assertEqual(result, ErrorCode.NOT_AUTHENTICATED)
        self.assertFalse(LocationPing.objects.exists())

    def test_ping_then_lock_commits_without_deadlock(self):
        self.assertEqual(self.race(self.record, lambda: lock_account(self.admin, self.shipper.pk, "Thử")), "ok")
        self.assertEqual(LocationPing.objects.count(), 1)
