from rest_framework.test import APIClient
from django.test import TestCase

from apps.accounts.models import User


class ERPStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "admin@test.local",
            "password123",
            full_name="Admin",
            employee_code="ADMIN-STATE",
            role="ADMINISTRATOR",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_state_round_trip(self):
        self.assertEqual(self.client.get("/api/erp-state/").json(), {"data": None, "revision": 0})
        database = {"purchaseInvoices": [{"id": "PI-1"}], "counters": {"PI": 1}}
        response = self.client.put("/api/erp-state/", {"data": database}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/erp-state/").json()["data"], database)

    def test_state_requires_object(self):
        response = self.client.put("/api/erp-state/", {"data": []}, format="json")
        self.assertEqual(response.status_code, 400)
