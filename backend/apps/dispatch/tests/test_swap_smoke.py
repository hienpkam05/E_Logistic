"""Ba kịch bản checklist qua API + session/CSRF/Origin/Referer; tự dọn bằng rollback test DB."""
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.dispatch.constants import DeliveryFailReason, TaskStatus
from apps.dispatch.models import Task, TaskResult
from apps.dispatch.tests.test_staff_swap import HUB, swap_fixture
from apps.shipments.constants import ShipmentStatus
from apps.shipments.tests.factories import PASSWORD, shipment_data


@override_settings(HUB=HUB)
class SwapSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        swap_fixture(cls)

    def setUp(self):
        self.clients = {}
        for index, user in enumerate((self.shop, self.admin, self.shipper, self.other)):
            client = Client(enforce_csrf_checks=True, REMOTE_ADDR=f"192.0.2.{index + 10}")
            client.get(reverse("auth-csrf"))
            self.http_post(client, reverse("auth-login"), {"username": user.username, "password": PASSWORD})
            self.clients[user.pk] = client

    def http_post(self, client, url, data=None, status=200):
        response = client.post(url, data or {}, content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            HTTP_ORIGIN="http://testserver", HTTP_REFERER="http://testserver/")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def create_approved(self):
        data = shipment_data(self.shipment.pickup_ward, self.shipment.delivery_ward)
        data["pickup_ward"] = self.shipment.pickup_ward.code
        data["delivery_ward"] = self.shipment.delivery_ward.code
        body = self.http_post(self.clients[self.shop.pk], reverse("shipment-list"), data, 201)
        self.pk = body["id"]
        self.staff_action("approve")
        return self.staff_action("assign-pickup", {"shipper_id": self.shipper.pk})

    def staff_action(self, action, data=None, status=200):
        client = self.clients[self.admin.pk]
        detail = client.get(reverse("shipment-detail", args=[self.pk])).json()
        return self.http_post(client, reverse("shipment-" + action, args=[self.pk]),
                              {"updated_at": detail["updated_at"], **(data or {})}, status)

    def task_action(self, user, task_id, action, data=None, status=200):
        return self.http_post(self.clients[user.pk], reverse("task-" + action, args=[task_id]), data, status)

    def delivery(self):
        pickup = self.create_approved()["tasks"][0]
        self.task_action(self.shipper, pickup["id"], "confirm-pickup")
        self.staff_action("receive-at-hub")
        return self.staff_action("assign-delivery", {"shipper_id": self.shipper.pk, "handed_over": True})["tasks"][0]

    def test_swap_before_receiving_goods(self):
        old = self.create_approved()["tasks"][0]
        body = self.staff_action("swap-shipper", {"shipper_id": self.other.pk, "reason": "Nghỉ"})
        new = body["tasks"][0]
        self.task_action(self.shipper, old["id"], "confirm-pickup", status=409)
        self.task_action(self.other, new["id"], "confirm-pickup")
        self.assertEqual(Task.objects.get(pk=old["id"]).status, TaskStatus.REPLACED)

    def test_swap_after_receiving_goods(self):
        old = self.delivery()
        self.staff_action("swap-shipper", {"shipper_id": self.other.pk, "reason": "Nghỉ"})
        self.task_action(self.shipper, old["id"], "confirm-delivery", {"cod_collected": 350000}, 409)
        self.task_action(self.other, old["id"], "report-swap-handover", status=404)
        self.task_action(self.shipper, old["id"], "report-swap-handover")
        new = self.staff_action("confirm-swap-handover", {"handed_over": True})["tasks"][0]
        self.assertEqual(new["attempt_no"], old["attempt_no"])
        self.task_action(self.other, new["id"], "confirm-delivery", {"cod_collected": 350000})
        self.assertEqual(TaskResult.objects.get(task_id=new["id"]).cod_collected, 350000)

    def test_three_attempts_with_swap_never_reset_counter(self):
        task = self.delivery()
        for attempt in range(1, 4):
            user = self.shipper if attempt < 3 else self.other
            if attempt == 3:
                self.staff_action("swap-shipper", {"shipper_id": self.other.pk, "reason": "Đổi người"})
                self.task_action(self.shipper, task["id"], "report-swap-handover")
                task = self.staff_action("confirm-swap-handover", {"handed_over": True})["tasks"][0]
                self.assertEqual(task["attempt_no"], 3)
            failure = {"reason_code": DeliveryFailReason.RECEIVER_UNREACHABLE}
            self.task_action(user, task["id"], "fail-delivery", failure)
            self.task_action(user, task["id"], "fail-delivery", failure)  # gửi lại không tăng số lần
            detail = self.clients[self.admin.pk].get(reverse("shipment-detail", args=[self.pk])).json()
            self.assertEqual(detail["delivery_attempts"], attempt)
            if attempt < 3:
                self.staff_action("decide-redelivery", {"reason": "Hẹn lại"})
                task = self.staff_action("assign-delivery", {"shipper_id": self.shipper.pk, "handed_over": True})["tasks"][0]
        self.staff_action("decide-redelivery", {"reason": "Thử vượt"}, 409)
        body = self.staff_action("decide-return", {"reason": "Đủ ba lần"})
        self.assertEqual(body["status"], ShipmentStatus.AWAITING_RETURN)
