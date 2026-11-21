import os
import sys


def main():
    # Console Windows (cp1252…) không in được tiếng Việt: thay ký tự lỗi bằng "?" thay vì làm sập lệnh.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
