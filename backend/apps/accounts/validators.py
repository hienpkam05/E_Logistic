"""Validator mật khẩu có thông điệp tiếng Việt cho các chuỗi bản dịch Django còn thiếu."""
from django.contrib.auth.password_validation import MinimumLengthValidator as DjangoMinimumLengthValidator


class MinimumLengthValidator(DjangoMinimumLengthValidator):
    def get_error_message(self):
        return f"Mật khẩu quá ngắn, cần ít nhất {self.min_length} ký tự."

    def get_help_text(self):
        return f"Mật khẩu cần ít nhất {self.min_length} ký tự."
