"""Đột biến GPS trong process con, không sửa source server; tái sử dụng runner spec 009."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
definition = importlib.util.spec_from_file_location(
    "spec009_mutations", ROOT / "specs/009-doi-shipper/tools/check_phase2_mutations.py")
runner = importlib.util.module_from_spec(definition)
definition.loader.exec_module(runner)
runner.LABEL = "apps.tracking.tests.test_location_ingest"
runner.MUTATIONS = [
    ("bỏ kiểm người phụ trách", "apps.dispatch.services",
     "tasks_visible_to(shipper)", "Task.objects.all()"),
    ("nhận điểm cho task đã đóng", "apps.tracking.services",
     "if task.status not in OPEN_TASK_STATUSES:", "if False:"),
    ("bỏ ngưỡng thời gian", "apps.tracking.services",
     "if age > PING_MAX_AGE_SECONDS or age < -PING_MAX_FUTURE_SECONDS or recorded_at < task.assigned_at:", "if False:"),
    ("bỏ nhịp máy chủ", "apps.tracking.services",
     "< PING_MIN_INTERVAL_SECONDS", "< 0"),
    ("nhận lại timestamp trùng hoặc lùi", "apps.tracking.services",
     "recorded_at <= latest.recorded_at", "False"),
    ("nhận điểm trước phân công", "apps.tracking.services",
     "or recorded_at < task.assigned_at", "or False"),
    ("bỏ kiểm lại user sau khóa", "apps.tracking.services",
     "lock_actor=True", "lock_actor=False"),
]

if __name__ == "__main__":
    runner.main()
