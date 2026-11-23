"""Chạy thao tác thật song song (dùng trong TransactionTestCase). Dùng chung spec 005–007+."""
import threading
import time

from django.db import connections, transaction

from apps.core.errors import BusinessError


class RaceMixin:
    HOLD_SECONDS = 0.5

    def race(self, first, second):
        """`first` chạy trong transaction, giữ khóa thêm HOLD_SECONDS; `second` bắt đầu khi first đã khóa.

        Trả kết quả của second: "ok", mã BusinessError, hoặc repr lỗi lạ. Lỗi ở first làm test thất bại.
        """
        locked, result = threading.Event(), {}

        def run_first():
            try:
                with transaction.atomic():
                    first()
                    locked.set()
                    time.sleep(self.HOLD_SECONDS)
            except Exception as exc:  # pragma: no cover - lộ lỗi bên đầu nếu có
                result["first"] = repr(exc)
                locked.set()
            finally:
                connections.close_all()

        def run_second():
            locked.wait(timeout=10)
            try:
                second()
                result["second"] = "ok"
            except BusinessError as exc:
                result["second"] = exc.code
            except Exception as exc:  # pragma: no cover
                result["second"] = repr(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=run_first), threading.Thread(target=run_second)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertNotIn("first", result, result.get("first"))
        return result["second"]

    def run_parallel(self, *actions):
        """Mọi thao tác xuất phát cùng lúc (Barrier) — vd 2 thiết bị bấm gần như đồng thời. Trả kết quả đã sắp."""
        start, results = threading.Barrier(len(actions)), []

        def run(action):
            start.wait()
            try:
                action()
                results.append("ok")
            except BusinessError as exc:
                results.append(exc.code)
            except Exception as exc:  # pragma: no cover
                results.append(repr(exc))
            finally:
                connections.close_all()

        threads = [threading.Thread(target=run, args=(a,)) for a in actions]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        return sorted(results)
