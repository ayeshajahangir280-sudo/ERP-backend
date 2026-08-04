from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.inventory.models import StockTransaction
from apps.inventory.services import get_available_stock, get_average_cost
from apps.inventory.posting import post_movement
from .models import CustomerLedger, SalesInvoice


@transaction.atomic
def post_sale(pk, user):
    invoice = SalesInvoice.objects.select_for_update().prefetch_related("items").get(pk=pk)
    if invoice.status not in {"DRAFT", "APPROVED"}:
        raise ValidationError("Only a draft or approved sales invoice can be posted.")
    items = list(invoice.items.select_related("finished_product", "unit"))
    if not items:
        raise ValidationError("At least one sales item is required.")
    subtotal = discount = vat = cogs = Decimal("0")
    costs = []
    for item in items:
        if item.quantity <= 0 or item.selling_price < 0:
            raise ValidationError("Quantities must be positive and prices non-negative.")
        StockTransaction.objects.select_for_update().filter(
            finished_product=item.finished_product,
            destination_location=invoice.sales_location,
        )
        available = get_available_stock(item.finished_product, invoice.sales_location)
        if item.quantity > available:
            raise ValidationError(f"Insufficient {item.finished_product.name}. Available: {available}.")
        gross = item.quantity * item.selling_price
        net = gross - item.discount_amount
        item.tax_amount = net * item.tax_rate / Decimal("100")
        item.line_total = net + item.tax_amount
        item.unit_cost_snapshot = get_average_cost(item.finished_product, invoice.sales_location)
        item.cost_total = item.quantity * item.unit_cost_snapshot
        item.gross_profit = net - item.cost_total
        item.save(update_fields=["tax_amount", "line_total", "unit_cost_snapshot", "cost_total", "gross_profit"])
        subtotal += gross; discount += item.discount_amount; vat += item.tax_amount; cogs += item.cost_total
        costs.append(item)
    revenue = subtotal - discount
    total = revenue + vat
    for item in costs:
        post_movement(item=item.finished_product,location=invoice.sales_location,quantity=item.quantity,direction="OUT",transaction_number=f"{invoice.invoice_number}-{item.id}",transaction_type="SALE",reference_type="SalesInvoice",reference_id=invoice.id,unit=item.unit,user=user,remarks=invoice.notes,audit_module="sales")
    invoice.subtotal=subtotal; invoice.discount_total=discount; invoice.vat_total=vat
    invoice.grand_total=total; invoice.cost_of_goods_sold=cogs
    invoice.gross_profit=revenue-cogs
    invoice.gross_margin_percentage=(invoice.gross_profit/revenue*Decimal("100")) if revenue else Decimal("0")
    invoice.outstanding_amount=total; invoice.status="POSTED"
    invoice.posted_at=timezone.now(); invoice.posted_by=user; invoice.save()
    CustomerLedger.objects.create(
        customer=invoice.customer, transaction_date=invoice.invoice_date,
        reference_type="SALE", reference_id=invoice.id, debit=total,
    )
    return invoice


@transaction.atomic
def cancel_sale(pk, user, reason):
    if not str(reason).strip(): raise ValidationError("Cancellation reason is required.")
    invoice=SalesInvoice.objects.select_for_update().get(pk=pk)
    if invoice.status not in {"POSTED", "PARTIALLY_PAID", "OVERDUE"}:
        raise ValidationError("Sales invoice cannot be cancelled.")
    originals=StockTransaction.objects.select_for_update().filter(reference_type="SalesInvoice",reference_id=invoice.id,is_reversal=False)
    for original in originals:
        if hasattr(original,"reversal"): raise ValidationError("Sales invoice was already reversed.")
        post_movement(item=original.finished_product,location=original.source_location,quantity=original.quantity_out,direction="IN",transaction_number=f"REV-{original.transaction_number}",transaction_type="SALE_REVERSAL",reference_type="SalesInvoice",reference_id=invoice.id,unit=original.unit,user=user,incoming_unit_cost=original.unit_cost,remarks=f"Sales cancellation: {reason}",reversal_of=original,is_reversal=True,audit_action="Reverse",audit_module="sales")
    CustomerLedger.objects.create(customer=invoice.customer,transaction_date=timezone.localdate(),reference_type="SALE_CANCELLATION",reference_id=invoice.id,credit=invoice.grand_total)
    invoice.status="CANCELLED";invoice.cancelled_at=timezone.now();invoice.cancelled_by=user
    invoice.cancellation_reason=reason;invoice.outstanding_amount=0;invoice.save();return invoice
