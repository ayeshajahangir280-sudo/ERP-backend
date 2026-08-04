from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.inventory.posting import post_movement
from apps.locations.models import Location
from apps.master_data.models import Customer,FinishedProduct,ItemCategory,Supplier,UnitOfMeasurement
from apps.purchasing.models import PurchaseInvoice,SupplierLedger
from apps.sales.models import CustomerLedger,SalesInvoice,SalesInvoiceItem

class ReportsDashboardTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user("report@test.local","password",full_name="Report",employee_code="REPORT",role="ADMINISTRATOR")
  self.client=APIClient();self.client.force_authenticate(self.user)
  self.unit=UnitOfMeasurement.objects.create(code="REP-U",name="Unit")
  category=ItemCategory.objects.create(name="REP-FG",kind="FG")
  self.product=FinishedProduct.objects.create(product_code="REP-P",name="Bread",category=category,sales_unit=self.unit,minimum_stock=Decimal("2"))
  self.location=Location.objects.create(code="REP-L",name="Shop",location_type="SHOP")
  self.customer=Customer.objects.create(customer_code="REP-C",name="Customer",opening_balance=Decimal("5"))
  self.supplier=Supplier.objects.create(supplier_code="REP-S",name="Supplier",opening_balance=Decimal("7"))
  post_movement(item=self.product,location=self.location,quantity=Decimal("10"),direction="IN",transaction_number="REP-IN",transaction_type="PRODUCTION_OUTPUT",reference_type="Test",reference_id=self.product.id,unit=self.unit,user=self.user,incoming_unit_cost=Decimal("2"))
  self.sale=SalesInvoice.objects.create(invoice_number="REP-SI",customer=self.customer,invoice_date=timezone.localdate(),sales_location=self.location,status="POSTED",grand_total=Decimal("50"),outstanding_amount=Decimal("30"),cost_of_goods_sold=Decimal("20"),gross_profit=Decimal("30"))
  SalesInvoiceItem.objects.create(sales_invoice=self.sale,finished_product=self.product,quantity=Decimal("5"),unit=self.unit,selling_price=Decimal("10"),line_total=Decimal("50"),cost_total=Decimal("20"),gross_profit=Decimal("30"))
  self.purchase=PurchaseInvoice.objects.create(invoice_number="REP-PI",supplier=self.supplier,invoice_date=timezone.localdate(),warehouse=self.location,status="POSTED",grand_total=Decimal("40"),outstanding_amount=Decimal("25"))
  CustomerLedger.objects.create(customer=self.customer,transaction_date=timezone.localdate(),reference_type="SalesInvoice",reference_id=self.sale.id,debit=Decimal("50"))
  SupplierLedger.objects.create(supplier=self.supplier,transaction_date=timezone.localdate(),reference_type="PurchaseInvoice",reference_id=self.purchase.id,credit=Decimal("40"))
 def test_inventory_and_ledger_reports_are_paginated_and_exportable(self):
  response=self.client.get("/api/reports/finished-goods-stock/?page_size=1");self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],1);self.assertEqual(response.data["results"][0]["quantity"],Decimal("10"))
  export=self.client.get("/api/reports/stock-ledger/?export=csv");self.assertEqual(export.status_code,200);self.assertEqual(export["Content-Type"],"text/csv")
 def test_financial_reports_reconcile_with_normalized_sources(self):
  customer=self.client.get("/api/reports/customer-outstanding/").data["results"][0];supplier=self.client.get("/api/reports/supplier-outstanding/").data["results"][0]
  self.assertEqual(customer["outstanding"],Decimal("55"));self.assertEqual(supplier["outstanding"],Decimal("47"))
 def test_dashboard_uses_backend_aggregates(self):
  response=self.client.get("/api/dashboard/");self.assertEqual(response.status_code,200);self.assertEqual(response.data["total_purchases"],Decimal("40"));self.assertEqual(response.data["daily_sales"],Decimal("50"));self.assertEqual(response.data["inventory_value"],Decimal("20"));self.assertEqual(response.data["receivables"],Decimal("30"));self.assertEqual(response.data["payables"],Decimal("25"))
 def test_location_permission_rejects_another_location(self):
  restricted=User.objects.create_user("restricted-report@test.local","password",full_name="Restricted",employee_code="REPORT-R",role="MANAGER",assigned_location=self.location,allowed_modules=["reports"])
  other=Location.objects.create(code="REP-O",name="Other",location_type="SHOP");self.client.force_authenticate(restricted)
  response=self.client.get(f"/api/reports/finished-goods-stock/?location={other.id}");self.assertEqual(response.status_code,400)
