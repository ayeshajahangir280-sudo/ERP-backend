from django.test import TestCase
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
