"""Kiểm quyền đọc/giới hạn task và retention, không sửa source server."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
definition = importlib.util.spec_from_file_location(
    "spec009_mutations", ROOT / "specs/009-doi-shipper/tools/check_phase2_mutations.py")
runner = importlib.util.module_from_spec(definition)
definition.loader.exec_module(runner)
runner.LABEL = "apps.tracking.tests"
runner.MUTATIONS = [
    ("bỏ phạm vi Shop", "apps.tracking.views", "shipments_visible_to(request.user).only",
     "shipments_visible_to(request.user).model.objects.only"),
    ("đọc cả task đã đóng", "apps.tracking.queries", ", status__in=OPEN_TASK_STATUSES", ""),
    ("lấy điểm task khác", "apps.tracking.queries", "filter(task_id=task_id)", "all()"),
    ("đánh dấu cũ sớm tại đúng biên", "apps.tracking.queries", "from django.db.models.lookups import LessThan",
     "from django.db.models.lookups import LessThanOrEqual as LessThan"),
    ("purge theo đồng hồ thiết bị", "apps.tracking.management.commands.purge_location_pings",
     "received_at__lt=cutoff", "recorded_at__lt=cutoff"),
    ("xóa cả điểm đúng biên retention", "apps.tracking.management.commands.purge_location_pings",
     "received_at__lt=cutoff", "received_at__lte=cutoff"),
]

if __name__ == "__main__":
    runner.main()
