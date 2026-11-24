"""Retention theo received_at máy chủ, chỉ xóa GPS quá hạn."""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.dispatch.models import Task
from apps.shipments.models import Shipment
from apps.tracking.models import LocationPing
from .test_location_ingest import prepare


class PurgeLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        prepare(cls)

    def ping(self, received_at, recorded_at=None):
        return LocationPing.objects.create(task=self.task, shipper=self.shipper, lat=0, lng=0,
            recorded_at=recorded_at or received_at, received_at=received_at)

    def purge(self, **options):
        output = StringIO()
        with patch("apps.tracking.management.commands.purge_location_pings.timezone.now", return_value=self.now):
            call_command("purge_location_pings", stdout=output, **options)
        return output.getvalue()

    def test_default_cutoff_strict_and_does_not_delete_business_rows(self):
        cutoff = self.now - timedelta(days=30)
        expired = self.ping(cutoff - timedelta(microseconds=1))
        edge = self.ping(cutoff)
        fresh = self.ping(cutoff + timedelta(microseconds=1))
        task, shipment = list(Task.objects.values()), list(Shipment.objects.values())
        self.assertIn("1", self.purge())
        self.assertFalse(LocationPing.objects.filter(pk=expired.pk).exists())
        self.assertSetEqual(set(LocationPing.objects.values_list("pk", flat=True)), {edge.pk, fresh.pk})
        self.assertEqual((list(Task.objects.values()), list(Shipment.objects.values())), (task, shipment))
        self.assertIn("0", self.purge())

    def test_cutoff_uses_received_not_device_clock(self):
        keep = self.ping(self.now, self.now - timedelta(days=40))
        expired = self.ping(self.now - timedelta(days=31), self.now)
        self.purge()
        self.assertTrue(LocationPing.objects.filter(pk=keep.pk).exists())
        self.assertFalse(LocationPing.objects.filter(pk=expired.pk).exists())

    def test_positive_days_override(self):
        self.ping(self.now - timedelta(days=2))
        edge = self.ping(self.now - timedelta(days=1))
        self.purge(days=1)
        self.assertEqual(list(LocationPing.objects.values_list("pk", flat=True)), [edge.pk])

    def test_invalid_days_does_not_delete(self):
        self.ping(self.now - timedelta(days=40))
        for value in (0, -1, True, 1.5, "bad", 10**20):
            with self.subTest(value=value), self.assertRaises(CommandError):
                self.purge(days=value)
        self.assertEqual(LocationPing.objects.count(), 1)
