from django.apps import AppConfig


class DispatchConfig(AppConfig):
    name = "apps.dispatch"
    verbose_name = "Điều phối"

    def ready(self):
        # D9 (spec 006): khóa Shipper còn nhiệm vụ mở → đánh dấu + báo Nhân viên. Đăng ký qua hook của accounts
        # để accounts không phải import dispatch (tránh phụ thuộc vòng).
        from apps.accounts.services import register_account_locked_hook

        from .services import flag_open_tasks_of_locked_shipper

        register_account_locked_hook(flag_open_tasks_of_locked_shipper)
