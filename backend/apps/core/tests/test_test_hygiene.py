"""Canh chất lượng bộ test: không lớp test nào được che method có sẵn của TestCase.

Lỗi đã gặp ở spec 006 Phase 3: lớp test có hàm tiện ích tên `fail` → che `TestCase.fail`, mà `assertEqual`
dùng `self.fail()` để báo lỗi → mọi assert sai trong file lặng lẽ "pass". Test này chặn lặp lại.
"""
import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TransactionTestCase

# Hook vòng đời được phép định nghĩa lại.
LIFECYCLE = {"setUp", "tearDown", "setUpClass", "tearDownClass", "setUpTestData", "databases"}


class TestClassesDoNotShadowTestCaseMethods(SimpleTestCase):
    def test_no_shadowing(self):
        builtin = {name for name in dir(TransactionTestCase) if not name.startswith("__")} - LIFECYCLE
        apps_dir = Path(settings.BASE_DIR) / "apps"
        hits = []
        for path in apps_dir.rglob("test*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
                for item in cls.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in builtin:
                        hits.append(f"{path.relative_to(apps_dir)}:{item.lineno} {cls.name}.{item.name}")
        self.assertGreater(len(builtin), 50)  # tự kiểm: danh sách method có sẵn thật sự được lấy
        self.assertEqual(hits, [], "Method che mất method có sẵn của TestCase — đổi tên")
