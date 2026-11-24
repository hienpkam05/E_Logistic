"""Chạy bằng manage.py shell -c exec(...); chỉ fixture ở test DB, rollback và không đổi sequence."""
from datetime import timedelta
import secrets
import sys

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Min
from django.test.utils import get_runner
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.dispatch.constants import TaskStatus, TaskType
from apps.dispatch.models import Task
from apps.shipments.models import Shipment, Ward
from apps.shipments.tests.factories import shipment_data
from apps.tracking.models import LocationPing
from apps.tracking.queries import current_task_location, latest_points


def sequence_state():
    state = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT schemaname, sequencename FROM pg_sequences WHERE schemaname = current_schema()")
        for schema, name in cursor.fetchall():
            qualified = connection.ops.quote_name(schema) + "." + connection.ops.quote_name(name)
            cursor.execute(f"SELECT last_value, is_called FROM {qualified}")
            state[name] = cursor.fetchone()
    return state


def below_ids(model, count=1):
    return min(model.objects.aggregate(low=Min("pk"))["low"] or 0, 0) - count - 1


def probe():
    assert connection.vendor == "postgresql"
    models = (User, Ward, Shipment, Task, LocationPing)
    before_counts = [model.objects.count() for model in models]
    before_sequences = sequence_state()
    with transaction.atomic():
        nonce = secrets.token_hex(5)
        users = []
        for i, role in enumerate((UserRole.SHOP, UserRole.ADMIN, UserRole.SHIPPER)):
            phone = "0" + str(secrets.randbelow(10**9)).zfill(9)
            while User.objects.filter(phone=phone).exists():
                phone = "0" + str(secrets.randbelow(10**9)).zfill(9)
            users.append(User.objects.create(id=below_ids(User), username=f"gps_plan_{nonce}_{i}",
                phone=phone, full_name="EXPLAIN rollback", role=role, password="!"))
        shop, admin, shipper = users
        ward = Ward.objects.create(id=below_ids(Ward), code=f"EX{nonce}", name="EXPLAIN rollback")
        request_number = 78_000_000
        while Shipment.objects.filter(request_code=Shipment.build_request_code(request_number)).exists():
            request_number += 1
        shipment = Shipment.objects.create(id=below_ids(Shipment), shop=shop,
            request_code=Shipment.build_request_code(request_number), **shipment_data(ward, ward))
        now = timezone.now()
        task = Task.objects.create(id=below_ids(Task), shipment=shipment, shipper=shipper, assigned_by=admin,
            type=TaskType.PICKUP, assigned_at=now - timedelta(days=4))
        old = Task.objects.create(id=below_ids(Task), shipment=shipment, shipper=shipper, assigned_by=admin,
            type=TaskType.PICKUP, status=TaskStatus.REPLACED, closed_at=now, assigned_at=now - timedelta(days=4))
        size = 20_000
        start = below_ids(LocationPing, size * 2)
        rows = [LocationPing(id=start + i, task=task, shipper=shipper, lat=21, lng=105,
                    recorded_at=now - timedelta(seconds=(size - i) * 15), received_at=now)
                for i in range(size)]
        rows += [LocationPing(id=start + size + i, task=old, shipper=shipper, lat=0, lng=0,
                    recorded_at=now, received_at=now) for i in range(size)]
        LocationPing.objects.bulk_create(rows, batch_size=1000)
        latest = latest_points(task.pk).first()
        assert latest.pk == start + size - 1
        current = current_task_location(shipment.pk, now).first()
        assert current["id"] == task.pk and current["location"]["lat"] == 21
        for label, query in (("Latest point: 20,000 target + 20,000 other task points", latest_points(task.pk)[:1]),
                             ("Current task + point, same SQL snapshot", current_task_location(shipment.pk, now).order_by("pk")[:1])):
            plan = query.explain(analyze=True, buffers=True)
            assert "Index Scan using location_task_latest_idx" in plan, plan
            print(label + ":")
            print(plan)
        transaction.set_rollback(True)
    assert [model.objects.count() for model in models] == before_counts
    assert sequence_state() == before_sequences
    print("Rollback sạch; sequence giữ nguyên. Không ép planner hoặc sửa thống kê.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    original_name = connection.settings_dict["NAME"]
    runner = get_runner(settings)(verbosity=0, interactive=False, keepdb=True)
    config = runner.setup_databases()
    try:
        assert connection.settings_dict["NAME"] != original_name, "Không được chạy fixture trên DB đang dùng"
        print("EXPLAIN trên PostgreSQL test DB; không migrate DB đang dùng.")
        probe()
    finally:
        runner.teardown_databases(config)


main()
