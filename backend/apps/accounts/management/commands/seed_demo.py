"""Tạo tài khoản demo cho môi trường phát triển (chỉ chạy khi DEBUG=True).

    python manage.py seed_demo                      # in mật khẩu ra màn hình
    python manage.py seed_demo --output .demo-accounts.txt
    python manage.py seed_demo --reset              # đặt lại mật khẩu + trạng thái demo của các tài khoản đã có
    python manage.py seed_demo --notifications      # thêm thông báo mẫu để thử danh sách/phân trang
    python manage.py seed_demo --wards              # thêm phường/xã DEMO (giả) khi chưa có danh sách chính thức

Mật khẩu sinh ngẫu nhiên mỗi lần tạo/đặt lại; tài khoản đã tồn tại không bị ghi đè nếu không có --reset.
Khi ghi --output vào file đã có, mật khẩu của tài khoản không đổi được giữ lại từ file cũ.
"""
import secrets
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.notifications.constants import NotificationKind
from apps.notifications.services import notify

# Số điện thoại dải 0999xxxxxx chỉ dùng cho dữ liệu giả.
DEMO_ACCOUNTS = [
    {"username": "demo_superuser", "full_name": "Quản trị hệ thống (demo)", "phone": "0999000001",
     "role": UserRole.ADMIN, "superuser": True},
    {"username": "demo_nhanvien", "full_name": "Nhân viên điều phối (demo)", "phone": "0999000002",
     "role": UserRole.ADMIN},
    {"username": "demo_shop", "full_name": "Shop Demo Hoàn Kiếm", "phone": "0999000003",
     "role": UserRole.SHOP, "address": "1 Tràng Tiền, Hoàn Kiếm, Hà Nội"},
    {"username": "demo_shipper", "full_name": "Shipper Demo", "phone": "0999000004",
     "role": UserRole.SHIPPER},
    # Thử luồng mật khẩu tạm (UC01.3): đăng nhập xong bị buộc đổi mật khẩu.
    {"username": "demo_mktam", "full_name": "Shop Mật khẩu tạm (demo)", "phone": "0999000005",
     "role": UserRole.SHOP, "must_change_password": True},
    # Thử tài khoản bị khóa (UC01.1 E1): đăng nhập báo lỗi chung như sai mật khẩu.
    {"username": "demo_khoa", "full_name": "Shipper Bị khóa (demo)", "phone": "0999000006",
     "role": UserRole.SHIPPER, "is_active": False},
]

# Phường/xã GIẢ để chạy thử khi chưa có danh sách chính thức (spec 004 D1). Mã DEMO-xx không trùng mã thật.
DEMO_WARDS = [
    ("DEMO-01", "Phường A"), ("DEMO-02", "Phường B"), ("DEMO-03", "Phường C"),
    ("DEMO-04", "Xã D"), ("DEMO-05", "Xã E"),
]

DEMO_NOTIFICATION_TITLE = "[Demo]"
# Số thông báo mẫu mỗi tài khoản; demo_shop nhiều hơn một trang (20) để thử phân trang.
DEMO_NOTIFICATION_COUNT = {"demo_shop": 25, "demo_nhanvien": 3, "demo_shipper": 3}
DEMO_NOTIFICATION_KINDS = [NotificationKind.REQUEST_APPROVED, NotificationKind.TASK_ASSIGNED, NotificationKind.DELIVERED]


def new_password():
    return secrets.token_urlsafe(12)


def read_previous_passwords(path):
    """{username: password} từ file --output cũ (bỏ dòng không có mật khẩu)."""
    if not path or not Path(path).exists():
        return {}
    result = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3 and not parts[2].startswith("("):
            result[parts[0]] = parts[2]
    return result


class Command(BaseCommand):
    help = "Tạo tài khoản demo cho mỗi vai trò (+ mật khẩu tạm, bị khóa). Chỉ dùng khi DEBUG=True."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="Ghi tên đăng nhập/mật khẩu vào file này thay vì in ra màn hình.")
        parser.add_argument("--reset", action="store_true",
                            help="Đặt lại mật khẩu và trạng thái demo (mật khẩu tạm, khóa) của tài khoản đã có.")
        parser.add_argument("--notifications", action="store_true",
                            help="Thêm thông báo mẫu (xóa thông báo mẫu cũ trước).")
        parser.add_argument("--wards", action="store_true",
                            help="Thêm phường/xã DEMO (giả, tiền tố [Demo]) khi chưa có danh sách chính thức.")

    def handle(self, *args, output=None, reset=False, notifications=False, wards=False, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo chỉ chạy khi DJANGO_DEBUG=True (không dùng cho production).")

        previous = read_previous_passwords(output)
        # Chỉ ghi/in mật khẩu sau khi DB đã commit, để file không bao giờ chứa mật khẩu của tài khoản bị rollback.
        with transaction.atomic():
            lines = self._seed(reset, previous)
            created_notes = self._seed_notifications() if notifications else 0
            created_wards = self._seed_wards() if wards else 0

        report = "Tài khoản demo HTT EXPRESS (chỉ dùng local)\n" + "\n".join(lines) + "\n"
        if output:
            path = Path(output)
            path.write_text(report, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Đã ghi {len(lines)} tài khoản vào {path.resolve()}"))
        else:
            self.stdout.write(report)
        if notifications:
            self.stdout.write(self.style.SUCCESS(f"Đã tạo {created_notes} thông báo mẫu."))
        if wards:
            self.stdout.write(self.style.SUCCESS(
                f"Phường/xã demo: thêm {created_wards}. Đây là dữ liệu GIẢ — thay bằng `load_wards <csv chính thức>`."))

    def _seed_wards(self):
        """Phường demo rõ ràng là giả (spec 004 D1). Không đụng phường thật đã nạp."""
        from apps.shipments.constants import DEMO_WARD_PREFIX
        from apps.shipments.models import Ward

        created = 0
        for code, name in DEMO_WARDS:
            _, is_new = Ward.objects.get_or_create(code=code, defaults={"name": f"{DEMO_WARD_PREFIX} {name}"})
            created += is_new
        return created

    def _seed(self, reset, previous):
        lines = []
        for spec in DEMO_ACCOUNTS:
            spec = dict(spec)
            is_superuser = spec.pop("superuser", False)
            username = spec["username"]
            user = User.objects.filter(username=username).first()

            if user and not reset:
                known = previous.get(username)
                note = known if known else "(không có trong file — chạy --reset để đặt lại)"
                lines.append(f"{username:<16} {user.role:<8} {note}   (đã tồn tại, giữ nguyên)")
                continue

            password = new_password()
            if user:
                user.set_password(password)
                user.must_change_password = spec.get("must_change_password", False)
                user.is_active = spec.get("is_active", True)
                user.save(update_fields=["password", "must_change_password", "is_active"])
                state = "đặt lại"
            elif is_superuser:
                User.objects.create_superuser(password=password, **spec)
                state = "tạo mới, superuser"
            else:
                User.objects.create_user(password=password, **spec)
                state = "tạo mới"
            flags = [f for f, on in (("mật khẩu tạm", spec.get("must_change_password")),
                                     ("bị khóa", spec.get("is_active") is False)) if on]
            lines.append(f"{username:<16} {spec['role']:<8} {password}   ({', '.join([state, *flags])})")
        return lines

    def _seed_notifications(self):
        from apps.notifications.models import Notification

        Notification.objects.filter(title__startswith=DEMO_NOTIFICATION_TITLE).delete()
        total = 0
        for username, count in DEMO_NOTIFICATION_COUNT.items():
            user = User.objects.filter(username=username).first()
            if not user:
                continue
            for i in range(1, count + 1):
                kind = DEMO_NOTIFICATION_KINDS[i % len(DEMO_NOTIFICATION_KINDS)]
                notify(user, kind, f"{DEMO_NOTIFICATION_TITLE} Thông báo mẫu số {i}",
                       body="Dữ liệu thử, không gắn với vận đơn thật.", payload={"demo": True})
                total += 1
        return total
