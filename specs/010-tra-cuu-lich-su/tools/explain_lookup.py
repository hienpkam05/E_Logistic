"""Chạy qua manage.py shell -c exec(...); fixture id âm, rollback, không đổi sequence."""
import secrets
import sys
from django.db import connection, transaction
from django.db.models import Min
from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.shipments.models import Shipment, Ward
from apps.shipments.queries import lookup_shipments
from apps.shipments.services import generate_tracking_code
from apps.shipments.tests.factories import shipment_data


def sequence_state():
    state = {}
    with connection.cursor() as cursor:
        cursor.execute('SELECT schemaname, sequencename FROM pg_sequences WHERE schemaname = current_schema()')
        for schema, name in cursor.fetchall():
            qualified = connection.ops.quote_name(schema) + '.' + connection.ops.quote_name(name)
            cursor.execute(f'SELECT last_value, is_called FROM {qualified}')
            state[name] = cursor.fetchone()
    return state


def below_ids(model, count=1):
    return min(model.objects.aggregate(low=Min('pk'))['low'] or 0, 0) - count - 1


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    assert connection.vendor == 'postgresql'
    before = sequence_state()
    models = (User, Ward, Shipment)
    counts = [model.objects.count() for model in models]
    with transaction.atomic():
        nonce = secrets.token_hex(5)
        users = []
        for i, role in enumerate((UserRole.SHOP, UserRole.ADMIN)):
            phone = '0' + str(secrets.randbelow(10**9)).zfill(9)
            while User.objects.filter(phone=phone).exists():
                phone = '0' + str(secrets.randbelow(10**9)).zfill(9)
            users.append(User.objects.create(id=below_ids(User), username=f'lookup_{nonce}_{i}',
                full_name='EXPLAIN lookup', phone=phone, role=role, password='!'))
        shop, admin = users
        ward = Ward.objects.create(id=below_ids(Ward), code=f'EX{nonce}', name='EXPLAIN rollback')
        size = 20000
        start = below_ids(Shipment, size)
        used = set(Shipment.objects.exclude(tracking_code=None).values_list('tracking_code', flat=True))
        request_base = 70_000_000
        while Shipment.objects.filter(request_code__in=[Shipment.build_request_code(request_base + i) for i in range(size)]).exists():
            request_base += size
        rows = []
        for i in range(size):
            tracking = generate_tracking_code()
            while tracking in used:
                tracking = generate_tracking_code()
            used.add(tracking)
            rows.append(Shipment(id=start + i, shop=shop, request_code=Shipment.build_request_code(request_base + i),
                tracking_code=tracking, **shipment_data(ward, ward)))
        Shipment.objects.bulk_create(rows, batch_size=1000)
        target = rows[size // 2]
        for user, role in ((shop, 'SHOP'), (admin, 'ADMIN')):
            for field in ('tracking_code', 'request_code'):
                query = lookup_shipments(user, getattr(target, field))
                assert query.count() == 1
                plan = query.explain(analyze=True, buffers=True)
                assert f'Index Scan using shipments_shipment_{field}_' in plan, plan
                assert 'InitPlan' in plan, plan
                print(f'{role}, {field}, 20,000 rows, no forced planner settings:')
                print(plan)
        transaction.set_rollback(True)
    assert [model.objects.count() for model in models] == counts
    assert sequence_state() == before
    print('Rollback sạch; sequence giữ nguyên.')


main()
