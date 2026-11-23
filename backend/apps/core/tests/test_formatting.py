from django.test import SimpleTestCase

from apps.core.formatting import format_vnd


class FormatVndTests(SimpleTestCase):
    def test_matches_frontend_format(self):
        """Cùng kết quả với formatVnd (frontend/src/utils/__tests__/format.spec.js)."""
        self.assertEqual(format_vnd(200_000), "200.000 ₫")
        self.assertEqual(format_vnd(0), "0 ₫")
        self.assertEqual(format_vnd(50_000_000), "50.000.000 ₫")
        self.assertEqual(format_vnd(999), "999 ₫")
