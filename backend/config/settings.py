import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
    "apps.accounts",
    "apps.shipments",
    "apps.dispatch",
    "apps.tracking",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("POSTGRES_DB", "htt_express"),
    "USER": os.getenv("POSTGRES_USER", "htt_express"),
    "PASSWORD": os.environ["POSTGRES_PASSWORD"],
    "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "PORT": os.getenv("POSTGRES_PORT", "5432"),
}}

AUTH_USER_MODEL = "accounts.User"

# Khi chạy `manage.py test`: dùng bộ băm nhanh để test đăng nhập không chậm.
# Không ảnh hưởng môi trường chạy thật (vẫn PBKDF2 mặc định).
if len(sys.argv) > 1 and sys.argv[1] == "test":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "apps.accounts.validators.MinimumLengthValidator"},  # thông điệp tiếng Việt
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.accounts.permissions.PasswordChangeNotRequired",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "EXCEPTION_HANDLER": "apps.core.exception_handler.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        # Chống dò mật khẩu: số lần gọi đăng nhập mỗi IP (spec 002 D3).
        "login": os.getenv("DJANGO_LOGIN_RATE", "10/min"),
        # Đổi mật khẩu, tính theo tài khoản: chặn dò mật khẩu hiện tại bằng phiên bị chiếm.
        "password_change": os.getenv("DJANGO_PASSWORD_CHANGE_RATE", "10/min"),
    },
}

# Phiên đăng nhập (spec 002 D2): hết hạn tuyệt đối sau SESSION_COOKIE_AGE giây, không gia hạn theo hoạt động.
SESSION_COOKIE_AGE = int(os.getenv("DJANGO_SESSION_AGE_SECONDS", "28800"))
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# Bật khi chạy HTTPS để cookie chỉ gửi qua kết nối mã hóa.
_SECURE_COOKIES = os.getenv("DJANGO_SECURE_COOKIES", "False").lower() == "true"
SESSION_COOKIE_SECURE = _SECURE_COOKIES
CSRF_COOKIE_SECURE = _SECURE_COOKIES

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Điểm tập kết duy nhất (spec 006 D6, spec 008 D6): Shipper đưa hàng hoàn về đây, Shop đến nhận lại hàng.
# Giá trị mặc định chỉ để demo — cấu hình thật trong backend/.env.
HUB = {
    "name": os.getenv("HUB_NAME", "Điểm tập kết HTT EXPRESS (demo)"),
    "address": os.getenv("HUB_ADDRESS", "Số 1 Phố Demo, Phường Demo, Hà Nội"),
    "phone": os.getenv("HUB_PHONE", "0900000000"),
}
