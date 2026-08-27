from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import StockTransaction
from apps.inventory.posting import post_movement
from apps.locations.models import Location
from apps.master_data.models import Customer, FinishedProduct, ItemCategory, RawMaterial, Supplier, UnitOfMeasurement
from apps.recipes.models import Recipe, RecipeItem


class MasterDeactivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("delete@test.local", "password", full_name="Admin", employee_code="DEL", role="ADMINISTRATOR")
        self.client = APIClient(); self.client.force_authenticate(self.user)
        self.unit = UnitOfMeasurement.objects.create(code="DEL-U", name="Unit")
        self.rm_category = ItemCategory.objects.create(name="Delete RM", kind="RM")
        self.fg_category = ItemCategory.objects.create(name="Delete FG", kind="FG")
        self.raw = RawMaterial.objects.create(material_code="DEL-RM", name="Flour", category=self.rm_category, base_unit=self.unit, purchase_unit=self.unit, consumption_unit=self.unit)
        self.product = FinishedProduct.objects.create(product_code="DEL-FG", name="Bread", category=self.fg_category, sales_unit=self.unit)
        self.location = Location.objects.create(code="DEL-L", name="Warehouse", location_type="RAW_MATERIAL_WAREHOUSE")
        self.customer = Customer.objects.create(customer_code="DEL-C", name="Customer", assigned_location=self.location)
        self.supplier = Supplier.objects.create(supplier_code="DEL-S", name="Supplier")
        self.recipe = Recipe.objects.create(recipe_number="DEL-R", finished_product=self.product, standard_output_quantity=1, output_unit=self.unit, version="1", effective_date=timezone.localdate(), status="ACTIVE", is_default=True)
        RecipeItem.objects.create(recipe=self.recipe, raw_material=self.raw, required_quantity=1, unit=self.unit)

    def test_item_deactivation_preserves_ledger_and_hides_operational_record(self):
        post_movement(item=self.raw, location=self.location, quantity=5, direction="IN", transaction_number="DEL-OPEN", transaction_type="OPENING_STOCK", reference_type="OpeningStock", reference_id=self.raw.id, unit=self.unit, user=self.user, incoming_unit_cost=2)
        self.assertEqual(self.client.delete(f"/api/raw-materials/{self.raw.id}/").status_code, 204)
        self.raw.refresh_from_db(); self.assertEqual(self.raw.status, "INACTIVE")
        self.assertTrue(StockTransaction.objects.filter(transaction_number="DEL-OPEN").exists())
        self.assertEqual(self.client.get("/api/raw-materials/").data["count"], 0)

    def test_all_historical_master_types_are_soft_deleted(self):
        targets = [
            (f"/api/finished-products/{self.product.id}/", self.product, "status"),
            (f"/api/customers/{self.customer.id}/", self.customer, "status"),
            (f"/api/suppliers/{self.supplier.id}/", self.supplier, "status"),
            (f"/api/locations/{self.location.id}/", self.location, "is_active"),
            (f"/api/recipes/{self.recipe.id}/", self.recipe, "status"),
        ]
        for url, instance, field in targets:
            self.assertEqual(self.client.delete(url).status_code, 204)
            instance.refresh_from_db()
            self.assertIn(getattr(instance, field), (False, "INACTIVE"))

    def test_recreating_deleted_category_reactivates_existing_row(self):
        self.assertEqual(self.client.delete(f"/api/categories/{self.rm_category.id}/").status_code, 204)
        self.rm_category.refresh_from_db()
        self.assertEqual(self.rm_category.status, "INACTIVE")

        response = self.client.post("/api/categories/", {"name": "Delete RM", "kind": "RM"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.rm_category.refresh_from_db()
        self.assertEqual(str(response.data["id"]), str(self.rm_category.id))
        self.assertEqual(self.rm_category.status, "ACTIVE")

    def test_recreating_deleted_unique_master_records_reactivates_existing_rows(self):
        targets = [
            (f"/api/suppliers/{self.supplier.id}/", "/api/suppliers/", self.supplier, {"supplier_code": "DEL-S", "name": "Supplier"}),
            (f"/api/customers/{self.customer.id}/", "/api/customers/", self.customer, {"customer_code": "DEL-C", "name": "Customer"}),
            (f"/api/units/{self.unit.id}/", "/api/units/", self.unit, {"code": "DEL-U", "name": "Unit"}),
            (f"/api/raw-materials/{self.raw.id}/", "/api/raw-materials/", self.raw, {"material_code": "DEL-RM", "name": "Flour", "category": self.rm_category.id, "base_unit": self.unit.id, "purchase_unit": self.unit.id, "consumption_unit": self.unit.id}),
            (f"/api/finished-products/{self.product.id}/", "/api/finished-products/", self.product, {"product_code": "DEL-FG", "name": "Bread", "category": self.fg_category.id, "sales_unit": self.unit.id}),
            (f"/api/locations/{self.location.id}/", "/api/locations/", self.location, {"code": "DEL-L", "name": "Warehouse", "location_type": "RAW_MATERIAL_WAREHOUSE"}),
        ]
        for delete_url, create_url, instance, payload in targets:
            self.assertEqual(self.client.delete(delete_url).status_code, 204)
            response = self.client.post(create_url, payload, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            instance.refresh_from_db()
            self.assertEqual(str(response.data["id"]), str(instance.id))
            if hasattr(instance, "status"):
                self.assertEqual(instance.status, "ACTIVE")
            else:
                self.assertTrue(instance.is_active)

    def test_recreating_deleted_recipe_reactivates_existing_row(self):
        self.assertEqual(self.client.delete(f"/api/recipes/{self.recipe.id}/").status_code, 204)
        response = self.client.post(
            "/api/recipes/",
            {
                "recipe_number": "DEL-R",
                "finished_product": self.product.id,
                "standard_output_quantity": 2,
                "output_unit": self.unit.id,
                "version": "2",
                "effective_date": timezone.localdate(),
                "status": "ACTIVE",
                "is_default": True,
                "items": [{"raw_material": self.raw.id, "required_quantity": 2, "unit": self.unit.id}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.recipe.refresh_from_db()
        self.assertEqual(str(response.data["id"]), str(self.recipe.id))
        self.assertEqual(self.recipe.status, "ACTIVE")
        self.assertEqual(self.recipe.version, "2")
