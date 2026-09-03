from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import StockTransaction
from apps.inventory.services import get_available_stock
from apps.locations.models import Location
from apps.master_data.models import FinishedProduct, ItemCategory, RawMaterial, UnitOfMeasurement
from apps.transfers.models import FinishedGoodsTransfer, MaterialTransfer


class TransferListTests(TestCase):
    endpoints = ("/api/material-transfers/", "/api/finished-goods-transfers/")

    def setUp(self):
        self.assigned = Location.objects.create(code="TL-A", name="Assigned", location_type="SHOP")
        self.other = Location.objects.create(code="TL-B", name="Other", location_type="SHOP")
        self.third = Location.objects.create(code="TL-C", name="Third", location_type="SHOP")
        self.admin = User.objects.create_user(
            "transfer-admin@test.local", "password", full_name="Admin", employee_code="TL-ADMIN",
            role="ADMINISTRATOR",
        )
        self.restricted = User.objects.create_user(
            "transfer-user@test.local", "password", full_name="Restricted", employee_code="TL-USER",
            role="WAREHOUSE", assigned_location=self.assigned,
            allowed_modules=["material_transfers", "stock_transfers"],
        )
        self.client = APIClient()
        self.unit = UnitOfMeasurement.objects.create(code="TL-U", name="Unit")
        self.rm_category = ItemCategory.objects.create(name="TL-RM", kind="RM")
        self.fg_category = ItemCategory.objects.create(name="TL-FG", kind="FG")
        self.raw_material = RawMaterial.objects.create(
            material_code="TL-RM-1", name="Flour", category=self.rm_category,
            base_unit=self.unit, purchase_unit=self.unit, consumption_unit=self.unit,
        )
        self.product = FinishedProduct.objects.create(
            product_code="TL-FG-1", name="Rusk", category=self.fg_category, sales_unit=self.unit,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def create_transfers(self):
        today = timezone.localdate()
        MaterialTransfer.objects.create(
            transfer_number="MT-ASSIGNED", transfer_date=today,
            source_location=self.assigned, destination_location=self.other,
        )
        MaterialTransfer.objects.create(
            transfer_number="MT-OTHER", transfer_date=today,
            source_location=self.other, destination_location=self.third,
        )
        FinishedGoodsTransfer.objects.create(
            transfer_number="FG-ASSIGNED", transfer_date=today,
            source_location=self.other, destination_location=self.assigned,
        )
        FinishedGoodsTransfer.objects.create(
            transfer_number="FG-OTHER", transfer_date=today,
            source_location=self.other, destination_location=self.third,
        )

    def test_administrator_lists_all_transfers(self):
        self.create_transfers()
        self.authenticate(self.admin)
        for endpoint in self.endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["count"], 2)

    def test_location_restricted_user_only_lists_related_transfers(self):
        self.create_transfers()
        self.authenticate(self.restricted)
        for endpoint in self.endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["count"], 1)
            result = response.json()["results"][0]
            self.assertIn(str(self.assigned.id), (result["source_location"], result["destination_location"]))

    def test_empty_transfer_tables_return_empty_lists(self):
        self.authenticate(self.admin)
        for endpoint in self.endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["count"], 0)
            self.assertEqual(response.json()["results"], [])

    def test_material_transfer_create_immediately_receives_and_moves_stock(self):
        self.authenticate(self.admin)
        StockTransaction.objects.create(
            transaction_number="TL-RM-OPEN", transaction_date=timezone.now(),
            transaction_type="OPENING_STOCK", reference_type="OpeningStock",
            reference_id=self.raw_material.id, raw_material=self.raw_material,
            destination_location=self.assigned, quantity_in=20, unit=self.unit,
            unit_cost=2, total_value=40, created_by=self.admin,
        )
        response = self.client.post(
            "/api/material-transfers/",
            {
                "transfer_date": timezone.localdate(),
                "source_location": self.assigned.id,
                "destination_location": self.other.id,
                "items": [{"raw_material": self.raw_material.id, "quantity": 5, "unit": self.unit.id}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "RECEIVED")
        self.assertEqual(get_available_stock(self.raw_material, self.assigned), Decimal("15.000"))
        self.assertEqual(get_available_stock(self.raw_material, self.other), Decimal("5.000"))

    def test_material_transfer_edit_reposts_received_stock_movements(self):
        self.authenticate(self.admin)
        StockTransaction.objects.create(
            transaction_number="TL-RM-CORR-OPEN", transaction_date=timezone.now(),
            transaction_type="OPENING_STOCK", reference_type="OpeningStock",
            reference_id=self.raw_material.id, raw_material=self.raw_material,
            destination_location=self.assigned, quantity_in=20, unit=self.unit,
            unit_cost=2, total_value=40, created_by=self.admin,
        )
        created = self.client.post(
            "/api/material-transfers/",
            {
                "transfer_date": timezone.localdate(),
                "source_location": self.assigned.id,
                "destination_location": self.other.id,
                "items": [{"raw_material": self.raw_material.id, "quantity": 1, "unit": self.unit.id}],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        updated = self.client.patch(
            f"/api/material-transfers/{created.data['id']}/",
            {"items": [{"raw_material": self.raw_material.id, "quantity": 11, "unit": self.unit.id}]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["items"][0]["quantity"], "11.000")
        self.assertEqual(updated.data["items"][0]["received_quantity"], "11.000")
        self.assertEqual(get_available_stock(self.raw_material, self.assigned), Decimal("9.000"))
        self.assertEqual(get_available_stock(self.raw_material, self.other), Decimal("11.000"))

    def test_finished_goods_transfer_create_immediately_receives_and_moves_stock(self):
        self.authenticate(self.admin)
        StockTransaction.objects.create(
            transaction_number="TL-FG-OPEN", transaction_date=timezone.now(),
            transaction_type="OPENING_STOCK", reference_type="OpeningStock",
            reference_id=self.product.id, finished_product=self.product,
            destination_location=self.assigned, quantity_in=20, unit=self.unit,
            unit_cost=2, total_value=40, created_by=self.admin,
        )
        response = self.client.post(
            "/api/finished-goods-transfers/",
            {
                "transfer_date": timezone.localdate(),
                "source_location": self.assigned.id,
                "destination_location": self.other.id,
                "items": [{"finished_product": self.product.id, "requested_quantity": 5, "unit": self.unit.id}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "RECEIVED")
        self.assertEqual(get_available_stock(self.product, self.assigned), Decimal("15.000"))
        self.assertEqual(get_available_stock(self.product, self.other), Decimal("5.000"))
