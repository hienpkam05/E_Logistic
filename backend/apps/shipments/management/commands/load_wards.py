"""Nạp danh mục phường/xã Hà Nội từ file CSV (spec 004 D1).

    python manage.py load_wards docs/data/hanoi_wards.csv
    python manage.py load_wards docs/data/hanoi_wards.csv --dry-run

File UTF-8 (chấp nhận BOM của Excel), dòng đầu là tiêu đề có cột `code` và `name`.
- Mã chưa có → thêm. Mã đã có → cập nhật tên, bật lại nếu đang ngừng dùng.
- Phường đang dùng mà không có trong file → ngừng dùng (is_active=False). KHÔNG xóa: đơn cũ vẫn tham chiếu.
Chạy lại cùng file không thay đổi gì. Lỗi bất kỳ dòng nào → không ghi gì.
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.shipments.models import Ward

REQUIRED_COLUMNS = {"code", "name"}


def read_rows(path):
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = {c.strip().lower() for c in (reader.fieldnames or [])}
            if not REQUIRED_COLUMNS <= columns:
                raise CommandError(f"File phải có cột: code, name (đang có: {', '.join(sorted(columns)) or 'không có'}).")
            rows, seen, errors = {}, set(), []
            for line_no, raw in enumerate(reader, start=2):
                row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
                code, name = row.get("code", ""), row.get("name", "")
                if not code and not name:
                    continue  # bỏ dòng trống
                if not code or not name:
                    errors.append(f"dòng {line_no}: thiếu mã hoặc tên")
                elif len(code) > 20 or len(name) > 100:
                    errors.append(f"dòng {line_no}: mã tối đa 20 ký tự, tên tối đa 100 ký tự")
                elif code in seen:
                    errors.append(f"dòng {line_no}: mã {code} bị lặp")
                else:
                    seen.add(code)
                    rows[code] = name
    except FileNotFoundError:
        raise CommandError(f"Không tìm thấy file: {path}") from None
    except UnicodeDecodeError:
        raise CommandError("File không phải UTF-8. Lưu lại bằng 'CSV UTF-8' rồi chạy lại.") from None
    if errors:
        raise CommandError("File có lỗi, chưa nạp gì:\n  " + "\n  ".join(errors[:20]))
    if not rows:
        raise CommandError("File không có dòng dữ liệu nào.")
    return rows


class Command(BaseCommand):
    help = "Nạp/cập nhật danh mục phường/xã Hà Nội từ CSV (cột code,name)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--dry-run", action="store_true", help="Chỉ báo sẽ thay đổi gì, không ghi.")

    def handle(self, csv_path, dry_run=False, **options):
        rows = read_rows(csv_path)
        stats = {"thêm": 0, "đổi tên": 0, "bật lại": 0, "ngừng dùng": 0, "không đổi": 0}
        with transaction.atomic():
            existing = {w.code: w for w in Ward.objects.select_for_update()}
            for code, name in rows.items():
                ward = existing.get(code)
                if ward is None:
                    Ward.objects.create(code=code, name=name)
                    stats["thêm"] += 1
                    continue
                changed = []
                if ward.name != name:
                    ward.name = name
                    changed.append("name")
                    stats["đổi tên"] += 1
                if not ward.is_active:
                    ward.is_active = True
                    changed.append("is_active")
                    stats["bật lại"] += 1
                if changed:
                    ward.save(update_fields=changed)
                else:
                    stats["không đổi"] += 1
            stale = [w.pk for code, w in existing.items() if code not in rows and w.is_active]
            stats["ngừng dùng"] = Ward.objects.filter(pk__in=stale).update(is_active=False)
            if dry_run:
                transaction.set_rollback(True)

        summary = ", ".join(f"{k}: {v}" for k, v in stats.items())
        prefix = "[Chạy thử — chưa ghi] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}{len(rows)} phường/xã trong file — {summary}."))
