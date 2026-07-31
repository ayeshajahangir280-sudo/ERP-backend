from django.test import TestCase
from django.db.utils import OperationalError
from unittest.mock import patch
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.locations.models import Location
class AccessTests(TestCase):
 def setUp(self):
  self.shop1=Location.objects.create(code="S1",name="Shop 1",location_type="SHOP");self.shop2=Location.objects.create(code="S2",name="Shop 2",location_type="SHOP")
  self.user=User.objects.create_user("shop1@test.local","password123",full_name="Shop 1",employee_code="S1",role="SALES",assigned_location=self.shop1,allowed_modules=["sales"])
  self.client=APIClient();self.client.force_authenticate(self.user)
 def test_assigned_module_allowed(self):self.assertEqual(self.client.get("/api/sales-invoices/").status_code,200)
 def test_unassigned_module_denied(self):self.assertEqual(self.client.get("/api/purchases/").status_code,403)
 def test_me_exposes_assignments(self):
  data=self.client.get("/api/auth/me/").json()["data"];self.assertEqual(data["allowed_modules"],["sales"]);self.assertEqual(data["assigned_location"],str(self.shop1.id))

 def test_health_reports_connected_database(self):
  response=self.client.get("/api/health/")
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json(),{"status":"ok","database":"connected"})

 @patch("config.urls.connection.ensure_connection",side_effect=OperationalError)
 def test_health_reports_unavailable_database(self,_ensure_connection):
  response=self.client.get("/api/health/")
  self.assertEqual(response.status_code,503)
  self.assertEqual(response.json(),{"status":"error","database":"unavailable"})
