"""Spec 010 Phase 1: tra cứu đúng mã, quyền, lịch sử có nhiệm vụ và phân trang ổn định."""
from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.serializers import EventActorSerializer
from apps.core.constants import SEARCH_QUERY_MAX_LENGTH
from apps.core.errors import ErrorCode
from apps.dispatch.constants import TaskStatus, TaskType
from apps.dispatch.models import Task, TaskResult
from apps.shipments.constants import ShipmentAction as A, ShipmentStatus as S
from apps.shipments.models import Shipment, ShipmentEvent
from apps.shipments.tests.factories import make_shipment, make_user, make_ward


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.shop = make_user('lookup_shop', '0900000001', full_name='Shop Hoa')
        cls.other = make_user('lookup_other', '0900000002', full_name='Shop khác')
        cls.admin = make_user('internal_admin', '0900000003', UserRole.ADMIN, full_name='Điều phối viên')
        cls.shipper = make_user('internal_shipper', '0900000004', UserRole.SHIPPER, full_name='Người giao hàng')
        cls.ward = make_ward()
        cls.shipment = make_shipment(cls.shop, cls.ward)
        cls.foreign = make_shipment(cls.other, cls.ward)
        Shipment.objects.filter(pk=cls.shipment.pk).update(tracking_code='HTT261123ABCDE')
        Shipment.objects.filter(pk=cls.foreign.pk).update(tracking_code='HTT261123FGHJK')
        cls.shipment.refresh_from_db()
        cls.foreign.refresh_from_db()

    def setUp(self):
        self.client.force_login(self.shop)

    def lookup(self, code):
        return self.client.get(reverse('shipment-lookup'), {'code': code})

    def history(self, **params):
        return self.client.get(reverse('shipment-events', args=[self.shipment.pk]), params)

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()['error']['code'], code)
        return response.json()['error']

    def make_event(self, action=A.CREATE_REQUEST, *, task=None, actor=None):
        return ShipmentEvent.objects.create(shipment=self.shipment, action=action, actor=actor,
            task=task, from_status=S.PENDING_APPROVAL, to_status=S.PENDING_APPROVAL)

    def make_task(self, task_type=TaskType.PICKUP, *, attempt=None):
        now = timezone.now()
        return Task.objects.create(shipment=self.shipment, type=task_type, shipper=self.shipper,
            assigned_by=self.admin, status=TaskStatus.REPLACED, closed_at=now, assigned_at=now,
            attempt_no=attempt)


class LookupTests(Base):
    def test_tracking_and_request_codes_normalized_without_rewriting_data(self):
        before = self.shipment.updated_at
        for code in (self.shipment.tracking_code, self.shipment.request_code):
            for value in (code, code.lower(), f' \t{code.lower()}\n '):
                with self.subTest(value=value):
                    body = self.ok(self.lookup(value))
                    self.assertEqual((body['id'], body['tracking_code'], body['request_code']),
                                     (self.shipment.pk, self.shipment.tracking_code, self.shipment.request_code))
                    self.assertIn('updated_at', body)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.updated_at, before)
        self.assertFalse(ShipmentEvent.objects.exists())
        self.assertFalse(Task.objects.exists())

    def test_request_code_works_before_approval(self):
        Shipment.objects.filter(pk=self.shipment.pk).update(tracking_code=None)
        body = self.ok(self.lookup(self.shipment.request_code.lower()))
        self.assertEqual(body['request_code'], self.shipment.request_code)
        self.assertIsNone(body['tracking_code'])

    def test_foreign_and_missing_have_identical_404_body(self):
        missing = self.lookup('HTT261123ZZZZZ')
        self.error(missing, 404, ErrorCode.NOT_FOUND)
        for code in (self.foreign.request_code, self.foreign.tracking_code, self.foreign.tracking_code.lower()):
            response = self.lookup(code)
            self.error(response, 404, ErrorCode.NOT_FOUND)
            self.assertEqual(response.content, missing.content)

    def test_staff_can_lookup_any_shop(self):
        self.client.force_login(self.admin)
        body = self.ok(self.lookup(self.foreign.tracking_code.lower()))
        self.assertEqual((body['id'], body['shop']['id']), (self.foreign.pk, self.other.pk))

    def test_roles_and_session_are_checked_before_query_validation(self):
        self.client.force_login(self.shipper)
        self.error(self.lookup(self.shipment.tracking_code), 403, ErrorCode.PERMISSION_DENIED)
        self.error(self.lookup(''), 403, ErrorCode.PERMISSION_DENIED)
        self.client.logout()
        self.error(self.lookup(''), 401, ErrorCode.NOT_AUTHENTICATED)

    def test_missing_blank_and_too_long_code_are_field_errors(self):
        responses = [self.client.get(reverse('shipment-lookup'))]
        responses += [self.lookup(code) for code in ('', ' \t\n ', 'X' * (SEARCH_QUERY_MAX_LENGTH + 1))]
        for response in responses:
            error = self.error(response, 400, ErrorCode.VALIDATION_ERROR)
            self.assertIn('code', error['fields'])
        self.error(self.lookup('X' * SEARCH_QUERY_MAX_LENGTH), 404, ErrorCode.NOT_FOUND)

    def test_lookup_does_not_do_substring_search_or_remove_internal_spaces(self):
        for code in (self.shipment.tracking_code[:-1], self.shipment.receiver_phone,
                     self.shipment.receiver_name, self.shipment.tracking_code[:3] + ' ' + self.shipment.tracking_code[3:]):
            self.error(self.lookup(code), 404, ErrorCode.NOT_FOUND)

    def test_lookup_adds_updated_at_without_changing_list_contract(self):
        lookup = self.ok(self.lookup(self.shipment.tracking_code))
        row = self.ok(self.client.get(reverse('shipment-list')))['results'][0]
        self.assertEqual(set(lookup), set(row) | {'updated_at'})
        self.assertNotIn('tasks', lookup)
        self.assertNotIn('holder_shipper', lookup)


class HistoryTests(Base):
    def test_empty_and_only_pretransport_history_return_false(self):
        empty = self.ok(self.history())
        self.assertEqual((empty['results'], empty['has_transport_activity']), ([], False))
        for action in (A.CREATE_REQUEST, A.UPDATE_REQUEST, A.CANCEL_REQUEST, A.APPROVE_REQUEST, A.REJECT_REQUEST):
            self.make_event(action, actor=self.admin)
        body = self.ok(self.history())
        self.assertEqual(body['count'], 5)
        self.assertFalse(body['has_transport_activity'])
        self.assertTrue(all(event['task'] is None for event in body['results']))

    def test_transport_flag_is_for_whole_shipment_not_just_the_page(self):
        first = self.make_event(A.APPROVE_REQUEST)
        self.make_event(A.ASSIGN_PICKUP, task=self.make_task(), actor=self.admin)
        page = self.ok(self.history(ordering='created_at', page_size=1))
        self.assertEqual(page['results'][0]['id'], first.pk)
        self.assertTrue(page['has_transport_activity'])
        second = self.ok(self.history(ordering='-created_at', page_size=1, page=2))
        self.assertEqual(second['results'][0]['id'], first.pk)
        self.assertTrue(second['has_transport_activity'])

    def test_pickup_numbers_stable_across_pages_ordering_and_timestamp_ties(self):
        first, second = self.make_task(), self.make_task()
        assigned = timezone.now()
        Task.objects.filter(pk__in=[first.pk, second.pk]).update(assigned_at=assigned)
        event1 = self.make_event(A.ASSIGN_PICKUP, task=first, actor=self.admin)
        event2 = self.make_event(A.SWAP_SHIPPER, task=first, actor=self.admin)
        event3 = self.make_event(A.ASSIGN_PICKUP, task=second, actor=self.admin)
        for ordering in ('created_at', '-created_at'):
            numbers = {}
            for page_number in (1, 2, 3):
                body = self.ok(self.history(ordering=ordering, page_size=1, page=page_number))
                event = body['results'][0]
                numbers[event['id']] = event['task']['pickup_no']
                self.assertIsNone(event['task']['attempt_no'])
            self.assertEqual(numbers, {event1.pk: 1, event2.pk: 1, event3.pk: 2})

    def test_delivery_replacement_keeps_attempt_and_task_null_for_unlinked_event(self):
        old = self.make_task(TaskType.DELIVERY, attempt=2)
        new = self.make_task(TaskType.DELIVERY, attempt=2)
        self.make_event(A.SWAP_SHIPPER, task=old, actor=self.admin)
        self.make_event(A.CONFIRM_SWAP_HANDOVER, task=old, actor=self.admin)
        self.make_event(A.FAIL_DELIVERY, task=new, actor=self.shipper)
        decision = self.make_event(A.DECIDE_REDELIVERY, actor=self.admin)
        body = self.ok(self.history())
        linked = [event['task'] for event in body['results'] if event['task']]
        self.assertEqual({task['id'] for task in linked}, {old.pk, new.pk})
        self.assertTrue(all(task['attempt_no'] == 2 and task['pickup_no'] is None for task in linked))
        self.assertIsNone(next(e for e in body['results'] if e['id'] == decision.pk)['task'])
        self.assertFalse(TaskResult.objects.exists())

    def test_shop_actor_has_name_but_no_internal_username_or_phone(self):
        self.make_event(actor=self.admin)
        self.make_event(A.ASSIGN_PICKUP, task=self.make_task(), actor=self.shipper)
        self.make_event()  # hệ thống
        body = self.ok(self.history())
        actors = [event['actor'] for event in body['results'] if event['actor']]
        self.assertEqual(len(actors), 2)
        for actor in actors:
            self.assertEqual(set(actor), {'id', 'full_name'})
        self.assertNotIn(self.admin.username, str(body))
        self.assertNotIn(self.shipper.username, str(body))
        self.assertIsNone(body['results'][0]['actor'])

    def test_staff_actor_keeps_existing_shape_shared_account_serializer_unchanged(self):
        self.make_event(actor=self.admin)
        self.client.force_login(self.admin)
        actor = self.ok(self.history())['results'][0]['actor']
        self.assertEqual(actor, {'id': self.admin.pk, 'username': self.admin.username, 'full_name': self.admin.full_name})
        self.assertEqual(EventActorSerializer(self.admin).data, actor)
        self.assertNotIn('phone', actor)

    def test_ordering_default_and_ties_are_stable_with_pagination(self):
        events = [self.make_event() for _ in range(3)]
        now = timezone.now()
        ShipmentEvent.objects.filter(pk__in=[event.pk for event in events]).update(created_at=now)
        ShipmentEvent.objects.filter(pk=events[1].pk).update(created_at=now - timedelta(seconds=1))
        ids = lambda body: [event['id'] for event in body['results']]
        self.assertEqual(ids(self.ok(self.history())), [events[2].pk, events[0].pk, events[1].pk])
        self.assertEqual(ids(self.ok(self.history(ordering='created_at'))), [events[1].pk, events[0].pk, events[2].pk])
        self.assertEqual(ids(self.ok(self.history(page_size=1, page=2))), [events[0].pk])

    def test_invalid_ordering_is_field_error_after_scope_check(self):
        for ordering in ('id', 'created_at,id', '', 'invalid'):
            error = self.error(self.history(ordering=ordering), 400, ErrorCode.VALIDATION_ERROR)
            self.assertIn('ordering', error['fields'])
        other = self.client.get(reverse('shipment-events', args=[self.foreign.pk]), {'ordering': 'invalid'})
        missing = self.client.get(reverse('shipment-events', args=[999999]), {'ordering': 'invalid'})
        self.error(other, 404, ErrorCode.NOT_FOUND)
        self.assertEqual(other.content, missing.content)

    def test_history_denies_foreign_shop_shipper_and_anonymous(self):
        self.make_event(actor=self.admin)
        self.client.force_login(self.other)
        self.error(self.history(), 404, ErrorCode.NOT_FOUND)
        self.client.force_login(self.shipper)
        self.error(self.history(), 403, ErrorCode.PERMISSION_DENIED)
        self.client.logout()
        self.error(self.history(), 401, ErrorCode.NOT_AUTHENTICATED)

    def test_history_no_n_plus_one_when_events_tasks_and_actors_increase(self):
        def add():
            self.make_event(A.ASSIGN_PICKUP, task=self.make_task(), actor=self.shipper)
        add()
        with CaptureQueriesContext(connection) as baseline:
            self.ok(self.history(page_size=100))
        for _ in range(24):
            add()
        with CaptureQueriesContext(connection) as expanded:
            self.assertEqual(self.ok(self.history(page_size=100))['count'], 25)
        self.assertEqual(len(baseline), len(expanded))

    def test_history_reads_do_not_change_saved_events_or_shipment(self):
        event = self.make_event(A.ASSIGN_PICKUP, task=self.make_task(), actor=self.admin)
        before = list(ShipmentEvent.objects.values())
        updated_at = self.shipment.updated_at
        self.ok(self.history(ordering='created_at'))
        self.ok(self.history())
        self.assertEqual(list(ShipmentEvent.objects.values()), before)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.updated_at, updated_at)
        self.assertEqual(ShipmentEvent.objects.get().pk, event.pk)
