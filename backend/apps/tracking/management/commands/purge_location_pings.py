"""Xóa GPS theo tuổi nhận máy chủ, không tác động dữ liệu giao nhận."""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.tracking.constants import LOCATION_RETENTION_DAYS
from apps.tracking.models import LocationPing


class Command(BaseCommand):
    help = "Xóa điểm GPS quá hạn theo received_at (mặc định theo thời hạn lưu của hệ thống)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=LOCATION_RETENTION_DAYS,
                            help="Số ngày lưu, phải là số nguyên dương; ghi nhận override khi vận hành.")

    def handle(self, *args, **options):
        days = options["days"]
        if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
            raise CommandError("--days phải là số nguyên dương.")
        try:
            cutoff = timezone.now() - timedelta(days=days)
        except OverflowError:
            raise CommandError("--days vượt phạm vi thời gian cho phép.")
        count, _ = LocationPing.objects.filter(received_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Đã xóa {count} điểm GPS (giữ {days} ngày)."))
