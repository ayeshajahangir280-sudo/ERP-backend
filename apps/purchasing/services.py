from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.inventory.models import StockTransaction
from .models import PurchaseInvoice,SupplierLedger
@transaction.atomic
def post_purchase(pk,user):
 inv=PurchaseInvoice.objects.select_for_update().prefetch_related("items").get(pk=pk)
 if inv.status not in ("DRAFT","APPROVED"): raise ValidationError("Only draft or approved purchases can be posted.")
 items=list(inv.items.all())
 if not items: raise ValidationError("At least one purchase item is required.")
 sub=discount=vat=Decimal("0")
 for i in items:
  if i.quantity<=0 or i.purchase_rate<0: raise ValidationError("Quantities must be positive and rates non-negative.")
  base=i.quantity*i.purchase_rate; i.tax_amount=(base-i.discount_amount)*i.tax_rate/Decimal("100"); i.line_total=base-i.discount_amount+i.tax_amount; i.save(update_fields=["tax_amount","line_total"]); sub+=base; discount+=i.discount_amount;vat+=i.tax_amount
  StockTransaction.objects.create(transaction_number=f"{inv.invoice_number}-{i.id}",transaction_date=timezone.now(),transaction_type="PURCHASE",reference_type="PurchaseInvoice",reference_id=inv.id,raw_material=i.raw_material,destination_location=inv.warehouse,quantity_in=i.quantity,unit=i.unit,unit_cost=i.purchase_rate,total_value=i.quantity*i.purchase_rate,created_by=user)
 total=sub-discount+vat; inv.subtotal=sub;inv.discount_total=discount;inv.vat_total=vat;inv.grand_total=total;inv.outstanding_amount=total;inv.status="POSTED";inv.posted_at=timezone.now();inv.posted_by=user;inv.save()
 SupplierLedger.objects.create(supplier=inv.supplier,transaction_date=inv.invoice_date,reference_type="PURCHASE",reference_id=inv.id,debit=total)
 return inv
@transaction.atomic
def cancel_purchase(pk,user,reason):
 if not reason: raise ValidationError("Cancellation reason is required.")
 inv=PurchaseInvoice.objects.select_for_update().get(pk=pk)
 if inv.status not in ("POSTED","PARTIALLY_PAID","OVERDUE"): raise ValidationError("Purchase cannot be cancelled.")
 originals=StockTransaction.objects.filter(reference_type="PurchaseInvoice",reference_id=inv.id,is_reversal=False)
 for o in originals:
  if hasattr(o,"reversal"): raise ValidationError("Purchase was already reversed.")
  StockTransaction.objects.create(transaction_number=f"REV-{o.transaction_number}",transaction_date=timezone.now(),transaction_type="PURCHASE_REVERSAL",reference_type="PurchaseInvoice",reference_id=inv.id,raw_material=o.raw_material,source_location=o.destination_location,quantity_out=o.quantity_in,unit=o.unit,unit_cost=o.unit_cost,total_value=-o.total_value,created_by=user,reversal_of=o,is_reversal=True)
 SupplierLedger.objects.create(supplier=inv.supplier,transaction_date=timezone.localdate(),reference_type="PURCHASE_CANCELLATION",reference_id=inv.id,credit=inv.grand_total)
 inv.status="CANCELLED";inv.cancelled_at=timezone.now();inv.cancelled_by=user;inv.cancellation_reason=reason;inv.save();return inv
