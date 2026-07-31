from django.db import models
from common.models import TransactionalModel,UUIDModel
class CustomerPayment(TransactionalModel):
 payment_number=models.CharField(max_length=50,unique=True);customer=models.ForeignKey("master_data.Customer",on_delete=models.PROTECT);payment_date=models.DateField();amount=models.DecimalField(max_digits=18,decimal_places=2);payment_method=models.ForeignKey("master_data.PaymentMethod",on_delete=models.PROTECT);reference_number=models.CharField(max_length=100,blank=True);notes=models.TextField(blank=True);status=models.CharField(max_length=20,default="DRAFT")
class CustomerPaymentAllocation(UUIDModel):
 payment=models.ForeignKey(CustomerPayment,on_delete=models.CASCADE,related_name="allocations");invoice=models.ForeignKey("sales.SalesInvoice",on_delete=models.PROTECT);amount=models.DecimalField(max_digits=18,decimal_places=2)
class SupplierPayment(TransactionalModel):
 payment_number=models.CharField(max_length=50,unique=True);supplier=models.ForeignKey("master_data.Supplier",on_delete=models.PROTECT);payment_date=models.DateField();amount=models.DecimalField(max_digits=18,decimal_places=2);payment_method=models.ForeignKey("master_data.PaymentMethod",on_delete=models.PROTECT);reference_number=models.CharField(max_length=100,blank=True);notes=models.TextField(blank=True);status=models.CharField(max_length=20,default="DRAFT")
class SupplierPaymentAllocation(UUIDModel):
 payment=models.ForeignKey(SupplierPayment,on_delete=models.CASCADE,related_name="allocations");invoice=models.ForeignKey("purchasing.PurchaseInvoice",on_delete=models.PROTECT);amount=models.DecimalField(max_digits=18,decimal_places=2)
