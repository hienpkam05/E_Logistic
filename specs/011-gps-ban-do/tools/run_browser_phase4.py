"""Chrome với API/session/CSRF và PostgreSQL test DB thật; không migrate DB người dùng."""
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
class GpsBrowser(LiveServerTestCase):
    host = '127.0.0.1'
    port = 8010

    def test_real_browser(self):
        swap_fixture(self)
        ward = self.shipment.pickup_ward
        def version(s):
            return Shipment.objects.get(pk=s.pk).updated_at
        def pickup(shop=None, shipper=None):
            s = create_request(shop or self.shop, shipment_data(ward, ward))
            approve_request(self.admin, s.pk, version(s))
            services.assign_pickup(self.admin, s.pk, (shipper or self.shipper).pk, version(s))
            return s
        def delivery():
            s = pickup()
            services.confirm_pickup(self.shipper, s.tasks.get(type=TaskType.PICKUP).pk)
            services.receive_at_hub(self.admin, s.pk, '', version(s))
            services.assign_delivery(self.admin, s.pk, self.shipper.pk, version(s))
            return s
        taking, delivering, returning = pickup(), delivery(), delivery()
        services.fail_delivery(self.shipper, returning.tasks.get(type=TaskType.DELIVERY).pk,
            DeliveryFailReason.RECEIVER_UNREACHABLE, '')
        services.decide_return(self.admin, returning.pk, 'Khách yêu cầu hoàn', version(returning))
        services.assign_return(self.admin, returning.pk, self.shipper.pk, version(returning))
        foreign = pickup(make_user('gps_foreign_shop', '0900000088'), self.other)
        output = ROOT / 'specs/011-gps-ban-do/artifacts/phase4'
        output.mkdir(parents=True, exist_ok=True)
        payload = dict(shop=self.shop.username, admin=self.admin.username, shipper=self.shipper.username,
            other=self.other.username, otherId=self.other.pk, password=PASSWORD, hub=HUB['address'],
            pickup=taking.tasks.get(type=TaskType.PICKUP).pk, pickupShipment=taking.pk,
            delivery=delivering.tasks.get(type=TaskType.DELIVERY).pk, deliveryShipment=delivering.pk,
            returning=returning.tasks.get(type=TaskType.RETURN).pk, foreign=foreign.pk, output=str(output))
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
                result = subprocess.run(['node', str(ROOT / 'specs/011-gps-ban-do/tools/browser_phase4.cjs')],
                    input=json.dumps(payload), text=True, encoding='utf-8', capture_output=True, timeout=240)
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
    failures = get_runner(settings)(verbosity=1, interactive=False, keepdb=True).run_tests(['__main__.GpsBrowser'])
    raise SystemExit(bool(failures))
