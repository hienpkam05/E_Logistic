r"""Kiểm Phase 2 bằng đột biến trong tiến trình con, không sửa source của server đang chạy.

Chạy từ gốc repo: venv\Scripts\python.exe specs/009-doi-shipper/tools/check_phase2_mutations.py
Mỗi biến thể phải làm test thất bại; mốc gốc phải đạt trước. Dùng PostgreSQL test DB, chạy tuần tự.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
LABEL = "apps.dispatch.tests.test_staff_swap"
MUTATIONS = [
    ("cho đổi nhiệm vụ hoàn", "apps.shipments.rules",
     "ShipmentAction.SWAP_SHIPPER: has_swappable_task,", "ShipmentAction.SWAP_SHIPPER: lambda s: True,"),
    ("nhận về khi còn nhiệm vụ / sai người giữ", "apps.shipments.rules",
     "ShipmentAction.RECALL_TO_HUB: recallable,", "ShipmentAction.RECALL_TO_HUB: lambda s: True,"),
    ("ghi sai lệch khi không chờ bàn giao", "apps.shipments.rules",
     "ShipmentAction.REPORT_SWAP_ISSUE: swap_pending,", "ShipmentAction.REPORT_SWAP_ISSUE: lambda s: True,"),
    ("bỏ kiểm phiên bản", "apps.shipments.services",
     "if shipment.updated_at != expected_updated_at:", "if False:"),
    ("cho chọn lại người cũ", "apps.dispatch.services",
     "if current.shipper_id == shipper_id:", "if False:"),
    ("cho người dự kiến bị khóa nhận nhiệm vụ", "apps.dispatch.services",
     "if candidate.role != UserRole.SHIPPER or not candidate.is_active:", "if False:"),
    ("đặt lại số lần giao", "apps.dispatch.services",
     "staff, attempt_no=task.attempt_no)", "staff, attempt_no=(1 if task.type == TaskType.DELIVERY else None))"),
    ("bỏ liên kết nhiệm vụ thay thế", "apps.dispatch.services",
     "task.replaced_by = new_task", "task.replaced_by = None"),
    ("không đổi người giữ hàng sau xác nhận", "apps.dispatch.services",
     "shipment.holder_type, shipment.holder_shipper = HolderType.SHIPPER, candidate",
     "shipment.holder_type, shipment.holder_shipper = HolderType.SHIPPER, task.shipper"),
    ("gửi nhầm thông báo cho người mới", "apps.dispatch.services",
     "notify(old_task.shipper, NotificationKind.TASK_REPLACED,",
     "notify(new_task.shipper, NotificationKind.TASK_REPLACED,"),
    ("không xóa cảnh báo nhiệm vụ cũ", "apps.dispatch.services",
     "task.needs_attention = False", "task.needs_attention = task.needs_attention"),
    ("bỏ transaction xác nhận bàn giao", "apps.dispatch.services",
     "def confirm_swap_handover(staff, shipment_id, discrepancy_note, expected_updated_at):\n    with transaction.atomic():",
     "def confirm_swap_handover(staff, shipment_id, discrepancy_note, expected_updated_at):\n    if True:"),
    ("bỏ khóa đơn", "apps.dispatch.services",
     "shipment = lock_visible(staff, shipment_id)", "shipment = Shipment.objects.get(pk=shipment_id)"),
]

RUNNER = r'''
import importlib, os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
module = importlib.import_module(sys.argv[1])
source = Path(module.__file__).read_text(encoding="utf-8")
if sys.argv[2] not in source:
    raise RuntimeError("Đích đột biến không còn khớp source")
exec(compile(source.replace(sys.argv[2], sys.argv[3]), module.__file__, "exec"), module.__dict__)
if sys.argv[1] == "apps.shipments.services":
    import apps.dispatch.services
    apps.dispatch.services.check_staff_action = module.check_staff_action
from django.test.utils import get_runner
from django.conf import settings
settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # như manage.py test
failures = get_runner(settings)(verbosity=0, keepdb=True, interactive=False).run_tests([sys.argv[4]])
sys.exit(1 if failures else 0)
'''


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    baseline = subprocess.run([sys.executable, "backend/manage.py", "test", LABEL, "--keepdb", "--noinput"], cwd=ROOT)
    if baseline.returncode:
        raise SystemExit("Mốc gốc thất bại: dừng, không tính đột biến.")
    survivors = []
    for name, module, before, after in MUTATIONS:
        result = subprocess.run([sys.executable, "-c", RUNNER, module, before, after, LABEL],
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        output = result.stdout + result.stderr
        # Lỗi khởi động / hạ tầng không được tính là test bắt được đột biến.
        caught = result.returncode == 1 and "FAILED (" in output
        print(("CAUGHT" if caught else "SURVIVED/ERROR") + ": " + name, flush=True)
        if not caught:
            survivors.append(name)
            print(output[-4000:], flush=True)
    print(f"Caught {len(MUTATIONS) - len(survivors)}/{len(MUTATIONS)}", flush=True)
    raise SystemExit(bool(survivors))


if __name__ == "__main__":
    main()
