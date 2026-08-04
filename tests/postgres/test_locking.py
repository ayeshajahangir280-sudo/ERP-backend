from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
import uuid
import unittest

from django.db import close_old_connections,connection
from django.test import TransactionTestCase,tag
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.inventory.models import InventoryBalance,StockTransaction
from apps.inventory.posting import post_movement
from apps.locations.models import Location
from apps.master_data.models import Customer,FinishedProduct,ItemCategory,PaymentMethod,UnitOfMeasurement
from apps.payments.models import CustomerPayment,CustomerPaymentAllocation
from apps.payments.services import cancel_payment,post_payment
from apps.sales.models import CustomerLedger,SalesInvoice,SalesInvoiceItem
from apps.sales.services import post_sale


@tag("postgres")
class PostgreSQLLockingTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor!="postgresql":raise unittest.SkipTest("PostgreSQL-only locking tests")
    def setUp(self):
        self.user=User.objects.create_user("pg@test.local","password",full_name="PG",employee_code="PG",role="ADMINISTRATOR")
        self.unit=UnitOfMeasurement.objects.create(code="PG-U",name="Unit")
        category=ItemCategory.objects.create(name="PG-FG",kind="FG")
        self.product=FinishedProduct.objects.create(product_code="PG-FG",name="Product",category=category,sales_unit=self.unit)
        self.location=Location.objects.create(code="PG-L",name="Shop",location_type="SHOP")
        self.customer=Customer.objects.create(customer_code="PG-C",name="Customer",assigned_location=self.location)
        self.method=PaymentMethod.objects.create(name="PG Bank")
    def concurrently(self,*operations):
        barrier=Barrier(len(operations))
        def invoke(operation):
            close_old_connections();barrier.wait()
            try:operation();return "ok"
            except (ValidationError,Exception) as exc:return exc.__class__.__name__
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:return list(pool.map(invoke,operations))
    def add_stock(self,quantity):
        post_movement(item=self.product,location=self.location,quantity=quantity,direction="IN",transaction_number=f"PG-IN-{uuid.uuid4()}",transaction_type="PRODUCTION_OUTPUT",reference_type="Test",reference_id=uuid.uuid4(),unit=self.unit,user=self.user,incoming_unit_cost=Decimal("2"))
    def invoice(self,number,quantity):
        invoice=SalesInvoice.objects.create(invoice_number=number,customer=self.customer,invoice_date=timezone.localdate(),sales_location=self.location,status="DRAFT")
        SalesInvoiceItem.objects.create(sales_invoice=invoice,finished_product=self.product,quantity=quantity,unit=self.unit,selling_price=Decimal("10"))
        return invoice
    def test_two_sales_cannot_oversell(self):
        self.add_stock(Decimal("5"));first=self.invoice("PG-S1",Decimal("4"));second=self.invoice("PG-S2",Decimal("4"))
        results=self.concurrently(lambda:post_sale(first.pk,self.user),lambda:post_sale(second.pk,self.user))
        balance=InventoryBalance.objects.get(finished_product=self.product,location=self.location)
        self.assertEqual(results.count("ok"),1);self.assertEqual(balance.current_quantity,Decimal("1"));self.assertGreaterEqual(balance.inventory_value,0);self.assertEqual(StockTransaction.objects.filter(transaction_type="SALE").count(),1)
    def test_concurrent_missing_balance_creation_has_one_row_and_no_lost_update(self):
        def incoming():post_movement(item=self.product,location=self.location,quantity=1,direction="IN",transaction_number=f"PG-CREATE-{uuid.uuid4()}",transaction_type="PRODUCTION_OUTPUT",reference_type="Test",reference_id=uuid.uuid4(),unit=self.unit,user=self.user,incoming_unit_cost=Decimal("2"))
        results=self.concurrently(incoming,incoming);balance=InventoryBalance.objects.get(finished_product=self.product,location=self.location)
        self.assertEqual(results,["ok","ok"]);self.assertEqual(InventoryBalance.objects.count(),1);self.assertEqual(balance.current_quantity,Decimal("2"));self.assertEqual(balance.average_unit_cost,Decimal("2"))
    def payment(self,number,invoice,amount):
        payment=CustomerPayment.objects.create(payment_number=number,customer=self.customer,payment_date=timezone.localdate(),amount=amount,payment_method=self.method)
        CustomerPaymentAllocation.objects.create(payment=payment,invoice=invoice,amount=amount);return payment
    def test_concurrent_payments_cannot_overallocate(self):
        invoice=self.invoice("PG-PAY-I",Decimal("1"));invoice.status="POSTED";invoice.grand_total=Decimal("100");invoice.outstanding_amount=Decimal("100");invoice.save()
        first=self.payment("PG-P1",invoice,Decimal("80"));second=self.payment("PG-P2",invoice,Decimal("80"))
        results=self.concurrently(lambda:post_payment(CustomerPayment,first.pk,self.user),lambda:post_payment(CustomerPayment,second.pk,self.user));invoice.refresh_from_db()
        self.assertEqual(results.count("ok"),1);self.assertEqual(invoice.outstanding_amount,Decimal("20"));self.assertEqual(CustomerLedger.objects.count(),1)
    def test_duplicate_post_and_cancel_have_single_financial_effect(self):
        invoice=self.invoice("PG-IDEM-I",Decimal("1"));invoice.status="POSTED";invoice.grand_total=Decimal("50");invoice.outstanding_amount=Decimal("50");invoice.save()
        payment=self.payment("PG-IDEM",invoice,Decimal("50"))
        self.assertEqual(self.concurrently(lambda:post_payment(CustomerPayment,payment.pk,self.user),lambda:post_payment(CustomerPayment,payment.pk,self.user)),["ok","ok"])
        self.assertEqual(CustomerLedger.objects.count(),1)
        self.assertEqual(self.concurrently(lambda:cancel_payment(CustomerPayment,payment.pk,self.user,"retry"),lambda:cancel_payment(CustomerPayment,payment.pk,self.user,"retry")),["ok","ok"])
        self.assertEqual(CustomerLedger.objects.count(),2);invoice.refresh_from_db();self.assertEqual(invoice.outstanding_amount,Decimal("50"))
