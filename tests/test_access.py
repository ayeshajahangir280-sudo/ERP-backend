from django.test import TestCase, override_settings
from django.db.utils import OperationalError
from unittest.mock import patch
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.accounts.serializers import UserAdminSerializer
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

 def test_created_user_without_modules_gets_role_defaults(self):
  serializer=UserAdminSerializer(data={"email":"sales-new@test.local","password":"password123","full_name":"Sales New","employee_code":"SNEW","role":"SALES","is_active":True})
  self.assertTrue(serializer.is_valid(),serializer.errors)
  user=serializer.save()
  self.assertIn("sales",user.allowed_modules)
  self.assertIn("dashboard",user.allowed_modules)

 def test_login_accepts_employee_code_username(self):
  user=User.objects.create_user("worker@test.local","password123",full_name="Worker",employee_code="WORKER1",role="SALES",allowed_modules=["sales"])
  client=APIClient()
  response=client.post("/api/auth/login/",{"email":"worker1","password":"password123"},format="json")
  self.assertEqual(response.status_code,200,response.content)
  self.assertEqual(response.json()["user"]["id"],str(user.id))

 def test_health_reports_connected_database(self):
  response=self.client.get("/api/health/")
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json(),{"status":"ok"})

 @patch("config.urls.connection.ensure_connection",side_effect=OperationalError)
 def test_health_reports_unavailable_database(self,_ensure_connection):
  response=self.client.get("/api/health/")
  self.assertEqual(response.status_code,503)
  self.assertEqual(response.json(),{"status":"error"})

 @override_settings(SECURE_SSL_REDIRECT=True)
 def test_internal_health_is_exempt_from_https_redirect(self):
  response=self.client.get("/api/health/",secure=False)
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json(),{"status":"ok"})

 @override_settings(SECURE_SSL_REDIRECT=True)
 def test_normal_api_route_still_redirects_to_https(self):
  response=self.client.get("/api/auth/me/",secure=False)
  self.assertEqual(response.status_code,301)
  self.assertTrue(response["Location"].startswith("https://"))
