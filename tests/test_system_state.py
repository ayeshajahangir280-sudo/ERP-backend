from rest_framework.test import APIClient
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import InventoryBalance,StockTransaction
from apps.locations.models import Location
from apps.master_data.models import ItemCategory,RawMaterial,UnitOfMeasurement
from apps.system_state.models import ERPState


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
        database = {"uiPreferences": {"dense": True}}
        response = self.client.put("/api/erp-state/", {"data": database, "revision": 0}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/erp-state/").json()["data"], database)

    def test_state_requires_object(self):
        response = self.client.put("/api/erp-state/", {"data": [], "revision": 0}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_stale_state_write_is_rejected(self):
        first=self.client.put("/api/erp-state/",{"data":{"uiPreferences":{}} ,"revision":0},format="json")
        self.assertEqual(first.status_code,200)
        stale=self.client.put("/api/erp-state/",{"data":{"uiPreferences":{"dense":True}},"revision":0},format="json")
        self.assertEqual(stale.status_code,409)
        self.assertEqual(self.client.get("/api/erp-state/").json()["data"],{"uiPreferences":{}})

    def test_transactional_collections_are_rejected(self):
        payload={"purchaseInvoices":[{"id":"fake"}],"stockLedger":[{"quantity":999}],"customerPayments":[{"amount":999}]}
        response=self.client.put("/api/erp-state/",{"data":payload,"revision":0},format="json")
        self.assertEqual(response.status_code,400)
        self.assertEqual(set(response.json()["rejected_keys"]),set(payload))
        self.assertFalse(ERPState.objects.exists())

    def test_nested_disguised_transactional_state_is_rejected(self):
        for preferences in ({"widgets":{"Stock_Ledger":[{"quantity":999}]}},{"PAYMENTS":{"fake":True}},{"layout":[{"purchaseInvoices":[]}]},):
            response=self.client.put("/api/erp-state/",{"data":{"uiPreferences":preferences},"revision":0},format="json")
            self.assertEqual(response.status_code,400)
        self.assertFalse(ERPState.objects.exists())

    def test_clear_business_data_requires_administrator(self):
        user=User.objects.create_user("staff@test.local","password123",full_name="Staff",employee_code="STAFF",role="SALES",allowed_modules=["dashboard"])
        self.client.force_authenticate(user)
        response=self.client.post("/api/system/clear-business-data/")
        self.assertEqual(response.status_code,403)

    def test_clear_business_data_removes_business_records_but_keeps_users(self):
        unit=UnitOfMeasurement.objects.create(code="KG",name="Kilogram")
        category=ItemCategory.objects.create(name="Flour",kind="RM")
        location=Location.objects.create(code="WH",name="Warehouse",location_type="RAW_MATERIAL_WAREHOUSE")
        material=RawMaterial.objects.create(material_code="FLOUR",name="Flour",category=category,base_unit=unit,purchase_unit=unit,consumption_unit=unit)
        InventoryBalance.objects.create(raw_material=material,location=location,current_quantity=10,inventory_value=20,average_unit_cost=2)
        StockTransaction.objects.create(transaction_number="ST-1",transaction_date=timezone.now(),transaction_type="OPENING_STOCK",reference_type="TEST",reference_id=material.id,raw_material=material,destination_location=location,quantity_in=10,unit=unit,unit_cost=2,total_value=20,created_by=self.user)

        response=self.client.post("/api/system/clear-business-data/")

        self.assertEqual(response.status_code,200,response.content)
        self.assertTrue(User.objects.filter(id=self.user.id).exists())
        self.assertFalse(StockTransaction.objects.exists())
        self.assertFalse(InventoryBalance.objects.exists())
        self.assertFalse(RawMaterial.objects.exists())
        self.assertFalse(Location.objects.exists())

        unit=UnitOfMeasurement.objects.create(code="KG",name="Kilogram")
        category=ItemCategory.objects.create(name="Flour",kind="RM")
        location=Location.objects.create(code="WH",name="Warehouse",location_type="RAW_MATERIAL_WAREHOUSE")
        material=RawMaterial.objects.create(material_code="FLOUR",name="Flour",category=category,base_unit=unit,purchase_unit=unit,consumption_unit=unit)
        self.assertEqual(material.material_code,"FLOUR")
