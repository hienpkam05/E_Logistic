import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.shipments.models import Ward

from .factories import make_shipment, make_user


class LoadWardsTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def csv(self, text, name="wards.csv", encoding="utf-8"):
        path = Path(self.tmp.name) / name
        path.write_bytes(text if isinstance(text, bytes) else text.encode(encoding))
        return str(path)

    def run_cmd(self, path, *args):
        out = StringIO()
        call_command("load_wards", path, *args, stdout=out)
        return out.getvalue()

    def active(self):
        return dict(Ward.objects.filter(is_active=True).values_list("code", "name"))

    def test_load_and_rerun_is_noop(self):
        path = self.csv("code,name\n001,Phường Một\n002,Xã Hai\n")
        self.run_cmd(path)
        self.assertEqual(self.active(), {"001": "Phường Một", "002": "Xã Hai"})
        out = self.run_cmd(path)
        self.assertIn("thêm: 0", out)
        self.assertIn("không đổi: 2", out)
        self.assertEqual(Ward.objects.count(), 2)

    def test_rename_deactivate_reactivate_never_delete(self):
        self.run_cmd(self.csv("code,name\n001,Phường Một\n002,Xã Hai\n"))
        self.run_cmd(self.csv("code,name\n001,Phường Một Mới\n"))
        self.assertEqual(self.active(), {"001": "Phường Một Mới"})
        self.assertFalse(Ward.objects.get(code="002").is_active)  # ngừng dùng, không xóa
        self.run_cmd(self.csv("code,name\n001,Phường Một Mới\n002,Xã Hai\n"))
        self.assertTrue(Ward.objects.get(code="002").is_active)

    def test_old_shipment_keeps_ward_name_after_deactivate(self):
        self.run_cmd(self.csv("code,name\n001,Phường Một\n"))
        shipment = make_shipment(make_user("shop_a", "0900000001"), Ward.objects.get(code="001"))
        self.run_cmd(self.csv("code,name\n999,Phường Khác\n"))
        shipment.refresh_from_db()
        self.assertEqual(shipment.delivery_ward.name, "Phường Một")
        self.assertFalse(shipment.delivery_ward.is_active)

    def test_excel_bom_and_column_case(self):
        self.run_cmd(self.csv("Code,Name\n001,Phường Một\n", encoding="utf-8-sig"))
        self.assertEqual(self.active(), {"001": "Phường Một"})

    def test_dry_run_writes_nothing(self):
        out = self.run_cmd(self.csv("code,name\n001,Phường Một\n"), "--dry-run")
        self.assertIn("Chạy thử", out)
        self.assertFalse(Ward.objects.exists())

    def test_invalid_files_write_nothing(self):
        cases = {
            "thiếu cột": "ma,ten\n001,Phường Một\n",
            "thiếu tên": "code,name\n001,\n",
            "mã lặp": "code,name\n001,A\n001,B\n",
            "rỗng": "code,name\n",
        }
        for label, text in cases.items():
            with self.subTest(label), self.assertRaises(CommandError):
                self.run_cmd(self.csv(text))
        with self.assertRaises(CommandError):
            self.run_cmd(self.csv(b"code,name\n001,Ph\xf0\xf2ng\n"))  # byte không hợp lệ UTF-8 (vd file ANSI cũ)
        with self.assertRaises(CommandError):
            self.run_cmd(str(Path(self.tmp.name) / "khong_co.csv"))
        self.assertFalse(Ward.objects.exists())

    def test_error_on_one_line_rolls_back_everything(self):
        self.run_cmd(self.csv("code,name\n001,Phường Một\n"))
        with self.assertRaises(CommandError):
            self.run_cmd(self.csv("code,name\n002,Xã Hai\n003,\n"))
        self.assertEqual(self.active(), {"001": "Phường Một"})

    def test_blank_lines_skipped(self):
        self.run_cmd(self.csv("code,name\n001,Phường Một\n,\n\n002,Xã Hai\n"))
        self.assertEqual(len(self.active()), 2)
