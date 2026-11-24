"""Chrome + API thật trên test DB, server riêng tự dọn; không dùng dữ liệu phiên người dùng."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.argv = ['manage.py', 'test']
import django
django.setup()
from django.conf import settings
from django.test import LiveServerTestCase, override_settings
from django.test.utils import get_runner
from apps.dispatch import services
from apps.dispatch.constants import DeliveryFailReason, TaskType
from apps.dispatch.tests.test_staff_swap import HUB, swap_fixture
from apps.shipments.models import Shipment
from apps.shipments.services import approve_request, create_request
from apps.shipments.tests.factories import PASSWORD, make_user, shipment_data


@override_settings(HUB=HUB)
class TrackingBrowser(LiveServerTestCase):
    host = '127.0.0.1'
    port = 8010

    def test_real_browser(self):
        swap_fixture(self)
        def version(s):
            return Shipment.objects.get(pk=s.pk).updated_at
        ward = self.shipment.pickup_ward
        s = create_request(self.shop, shipment_data(ward, ward))
        approve_request(self.admin, s.pk, version(s))
        services.assign_pickup(self.admin, s.pk, self.shipper.pk, version(s))
        services.confirm_pickup(self.shipper, s.tasks.get(type=TaskType.PICKUP).pk)
        services.receive_at_hub(self.admin, s.pk, '', version(s))
        services.assign_delivery(self.admin, s.pk, self.shipper.pk, version(s))
        services.fail_delivery(self.shipper, s.tasks.get(type=TaskType.DELIVERY).pk,
                               DeliveryFailReason.RECEIVER_UNREACHABLE, '')
        services.decide_redelivery(self.admin, s.pk, 'Hẹn lại', version(s))
        services.assign_delivery(self.admin, s.pk, self.shipper.pk, version(s))
        services.swap_shipper(self.admin, s.pk, self.other.pk, 'Nghỉ', version(s))
        s.refresh_from_db()
        other_shop = make_user('tracking_other_shop', '0900000099')
        foreign = create_request(other_shop, shipment_data(ward, ward))
        approve_request(self.admin, foreign.pk, version(foreign))
        foreign.refresh_from_db()
        pending = create_request(self.shop, shipment_data(ward, ward))
        phase = os.environ.get('SPEC010_BROWSER_PHASE', 'phase2')
        if phase not in {'phase2', 'phase3'}:
            raise ValueError('SPEC010_BROWSER_PHASE chỉ nhận phase2 hoặc phase3')
        output = ROOT / 'specs/010-tra-cuu-lich-su/artifacts' / phase
        output.mkdir(parents=True, exist_ok=True)
        payload = dict(shop=self.shop.username, admin=self.admin.username, shipper=self.shipper.username,
                       password=PASSWORD, code=s.tracking_code, foreign=foreign.tracking_code,
                       request=pending.request_code, output=str(output))
        with (output / 'vite.log').open('w', encoding='utf-8') as log:
            vite = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', self.host, '--port', '5180', '--strictPort'],
                cwd=ROOT / 'frontend', env={**os.environ, 'VITE_PROXY_TARGET': self.live_server_url},
                stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                for _ in range(50):
                    if vite.poll() is not None: raise RuntimeError('Vite không khởi động')
                    try:
                        with urlopen('http://127.0.0.1:5180', timeout=1): break
                    except OSError: time.sleep(.2)
                result = subprocess.run(['node', str(ROOT / 'specs/010-tra-cuu-lich-su/tools/browser_phase2.cjs')],
                    input=json.dumps(payload), text=True, encoding='utf-8', capture_output=True, timeout=180)
                print(result.stdout)
                self.assertEqual(result.returncode, 0, result.stderr)
            finally:
                vite.terminate()
                vite.wait(timeout=15)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for port in (8010, 5180):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0: raise SystemExit(f'Cổng {port} đang dùng, không dừng server khác')
    failures = get_runner(settings)(verbosity=1, interactive=False, keepdb=True).run_tests(['__main__.TrackingBrowser'])
    raise SystemExit(bool(failures))
