"""Browser thật + API/PostgreSQL thật trên test DB; server riêng 8010/5180, tự dọn khi kết thúc."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
os.chdir(ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.argv = ['manage.py', 'test']  # cấu hình băm nhanh của dự án, chỉ dùng trong test process
import django
django.setup()
from django.conf import settings
from django.test import LiveServerTestCase, override_settings
from django.test.utils import get_runner
from apps.dispatch import services
from apps.dispatch.constants import DeliveryFailReason, TaskType
from apps.dispatch.tests.test_staff_swap import HUB, swap_fixture
from apps.shipments.models import Shipment
from apps.shipments.services import approve_request
from apps.shipments.tests.factories import PASSWORD, make_shipment


@override_settings(HUB=HUB)
class BrowserPhase5(LiveServerTestCase):
    host = '127.0.0.1'
    port = 8010

    def test_real_browser(self):
        swap_fixture(self)
        def version(s):
            return Shipment.objects.get(pk=s.pk).updated_at
        def pickup():
            s = make_shipment(self.shop, self.shipment.pickup_ward)
            approve_request(self.admin, s.pk, version(s))
            services.assign_pickup(self.admin, s.pk, self.shipper.pk, version(s))
            return s, s.tasks.get(type=TaskType.PICKUP)
        first, first_task = pickup()
        second, second_task = pickup()
        services.confirm_pickup(self.shipper, second_task.pk)
        services.receive_at_hub(self.admin, second.pk, '', version(second))
        services.assign_delivery(self.admin, second.pk, self.shipper.pk, version(second))
        task = second.tasks.get(type=TaskType.DELIVERY)
        services.fail_delivery(self.shipper, task.pk, DeliveryFailReason.RECEIVER_UNREACHABLE, '')
        services.decide_redelivery(self.admin, second.pk, 'Hẹn lại', version(second))
        services.assign_delivery(self.admin, second.pk, self.shipper.pk, version(second))
        current = second.tasks.get(type=TaskType.DELIVERY, attempt_no=2)
        artifact_name = os.getenv('SPEC009_BROWSER_ARTIFACTS', 'phase5')
        if artifact_name not in ('phase5', 'phase6'):
            raise ValueError('Thư mục artifact không hợp lệ')
        output = ROOT / 'specs/009-doi-shipper/artifacts' / artifact_name
        output.mkdir(parents=True, exist_ok=True)
        payload = dict(admin=self.admin.username, old=self.shipper.username, next=self.other.username,
                       oldName=self.shipper.full_name, newName=self.other.full_name, password=PASSWORD,
                       nextId=self.other.pk, pickup=first.pk, pickupTask=first_task.pk,
                       delivery=second.pk, deliveryTask=current.pk, output=str(output))
        environment = {**os.environ, 'VITE_PROXY_TARGET': self.live_server_url}
        with (output / 'vite.log').open('w', encoding='utf-8') as log:
            vite = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', self.host,
                                     '--port', '5180', '--strictPort'], cwd=ROOT / 'frontend', env=environment,
                                    stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                for _ in range(50):
                    if vite.poll() is not None:
                        raise RuntimeError('Vite không khởi động; xem artifacts/phase5/vite.log')
                    try:
                        with urlopen('http://127.0.0.1:5180', timeout=1):
                            break
                    except OSError:
                        time.sleep(.2)
                result = subprocess.run(['node', str(ROOT / 'specs/009-doi-shipper/tools/browser_phase5.cjs')],
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
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise SystemExit(f'Port {port} đang được dùng; không dừng tiến trình khác.')
    failures = get_runner(settings)(verbosity=1, interactive=False, keepdb=True).run_tests(['__main__.BrowserPhase5'])
    raise SystemExit(bool(failures))
