"""Chạy qua manage.py shell -c exec(...); fixture dùng id âm và luôn rollback, không gọi nextval."""
import secrets
import sys

from django.db import connection, transaction
from django.db.models import Min
from django.utils import timezone

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.dispatch.constants import OPEN_TASK_STATUSES, TaskStatus, TaskType
from apps.dispatch.models import Task
from apps.shipments.models import Shipment, Ward
from apps.shipments.tests.factories import shipment_data


def sequences():
    with connection.cursor() as cursor:
        cursor.execute("SELECT schemaname, sequencename FROM pg_sequences WHERE schemaname = current_schema()")
        result = {}
        for schema, name in cursor.fetchall():
            qualified = connection.ops.quote_name(schema) + "." + connection.ops.quote_name(name)
            cursor.execute(f"SELECT last_value, is_called FROM {qualified}")
            result[name] = cursor.fetchone()
        return result


def negative_start(model, size=1):
    return min(model.objects.aggregate(low=Min("pk"))["low"] or 0, 0) - size - 1


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    assert connection.vendor == "postgresql"
    models = (User, Ward, Shipment, Task)
    before_counts = [m.objects.count() for m in models]
    before_sequences = sequences()
    size = 20000
    with transaction.atomic():
        nonce = secrets.token_hex(5)
        start = negative_start(User, 4)
        users = []
        for i, role in enumerate((UserRole.ADMIN, UserRole.SHOP, UserRole.SHIPPER, UserRole.SHIPPER)):
            phone = "0" + str(secrets.randbelow(10**9)).zfill(9)
            while User.objects.filter(phone=phone).exists():
                phone = "0" + str(secrets.randbelow(10**9)).zfill(9)
            users.append(User.objects.create(id=start + i, username=f"explain_{nonce}_{i}", full_name="EXPLAIN",
                                             phone=phone, role=role, password="!"))
        admin, shop, target, other = users
        ward = Ward.objects.create(id=negative_start(Ward), code=f"EX{nonce}", name="EXPLAIN rollback")
        first = negative_start(Shipment, size)
        shipments = [Shipment(id=first + i, shop=shop, **shipment_data(ward, ward)) for i in range(size)]
        Shipment.objects.bulk_create(shipments, batch_size=1000)
        first_task = negative_start(Task, size)
        now = timezone.now()
        tasks = []
        for i, shipment in enumerate(shipments):
            # Người cần xem có 20 nhiệm vụ mở, 980 đã đóng giữa 20.000 nhiệm vụ.
            active = i < 20 or i >= 1000
            tasks.append(Task(id=first_task + i, shipment=shipment, shipper=target if i < 1000 else other,
                              assigned_by=admin, type=TaskType.PICKUP,
                              status=TaskStatus.ACTIVE if active else TaskStatus.REPLACED,
                              closed_at=None if active else now))
        Task.objects.bulk_create(tasks, batch_size=1000)
        query = Task.objects.filter(shipper=target, status__in=OPEN_TASK_STATUSES).select_related("shipment")
        assert query.count() == 20
        print("Fixture: 20,000 tasks; target has 20 open + 980 closed; no forced planner settings.")
        print(query.explain(analyze=True, buffers=True))
        transaction.set_rollback(True)
    assert [m.objects.count() for m in models] == before_counts, "Fixture chưa rollback"
    assert sequences() == before_sequences, "Sequence đã thay đổi"
    print("Rollback sạch; sequence giữ nguyên.")


main()
