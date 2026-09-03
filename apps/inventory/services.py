from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum,Q,DecimalField,Case,When,F,Value
from django.db.models.functions import Coalesce,Abs
from .models import InventoryBalance,StockTransaction
ZERO=Decimal("0")
MONEY=Decimal("0.0001")
def _stock(qs): return qs.aggregate(v=Coalesce(Sum("quantity_in")-Sum("quantity_out"),ZERO,output_field=DecimalField()))["v"]
def _ledger_totals(field,item,location):
 qs=StockTransaction.objects.filter(**{field:item}).filter(Q(destination_location=location)|Q(source_location=location))
 return qs.aggregate(
  quantity=Coalesce(Sum(F("quantity_in")-F("quantity_out")),ZERO,output_field=DecimalField()),
  value=Coalesce(Sum(Case(
   When(destination_location=location,then=Abs(F("total_value"))),
   When(source_location=location,then=-Abs(F("total_value"))),
   default=Value(ZERO),output_field=DecimalField(max_digits=18,decimal_places=4),
  )),ZERO,output_field=DecimalField()),
 )
def sync_inventory_balance(item,location):
 field="raw_material" if item._meta.model_name=="rawmaterial" else "finished_product"
 totals=_ledger_totals(field,item,location)
 lookup={field:item,"location":location}
 balance=InventoryBalance.objects.filter(**lookup).first()
 if not balance:
  return totals
 value=max(ZERO,totals["value"]).quantize(MONEY,rounding=ROUND_HALF_UP)
 average=(value/totals["quantity"]).quantize(MONEY,rounding=ROUND_HALF_UP) if totals["quantity"]>0 else ZERO
 if balance.current_quantity!=totals["quantity"] or balance.inventory_value!=value or balance.average_unit_cost!=average:
  balance.current_quantity=totals["quantity"];balance.inventory_value=value;balance.average_unit_cost=average;balance.revision+=1
  balance.save(update_fields=["current_quantity","inventory_value","average_unit_cost","revision","updated_at"])
 return {"quantity":balance.current_quantity,"value":balance.inventory_value}
def get_raw_material_stock(material,location): return _stock(StockTransaction.objects.filter(raw_material=material).filter(Q(destination_location=location)|Q(source_location=location)))
def get_finished_product_stock(product,location,batch=None):
 """Combined product stock. ``batch`` is accepted only for API compatibility."""
 qs=StockTransaction.objects.filter(finished_product=product).filter(Q(destination_location=location)|Q(source_location=location))
 return _stock(qs)
def get_available_stock(item,location):
 field="raw_material" if item._meta.model_name=="rawmaterial" else "finished_product"
 balance=InventoryBalance.objects.filter(**{field:item},location=location).first()
 if balance:
  return sync_inventory_balance(item,location)["quantity"]
 return get_raw_material_stock(item,location) if field=="raw_material" else get_finished_product_stock(item,location)
def get_average_cost(item,location):
 """Current moving balance value / quantity for an item at one location."""
 field="raw_material" if item._meta.model_name=="rawmaterial" else "finished_product"
 balance=InventoryBalance.objects.filter(**{field:item},location=location).first()
 if balance:
  sync_inventory_balance(item,location)
  balance.refresh_from_db(fields=["average_unit_cost"])
  return balance.average_unit_cost
 totals=_ledger_totals(field,item,location)
 return totals["value"]/totals["quantity"] if totals["quantity"]>0 else ZERO
def get_stock_by_location(item):
 from apps.locations.models import Location
 return {str(x.id):get_available_stock(item,x) for x in Location.objects.filter(is_inventory_location=True)}
def get_inventory_valuation(location=None):
 qs=StockTransaction.objects.all()
 if location:
  qs=qs.filter(Q(destination_location=location)|Q(source_location=location))
  return qs.aggregate(v=Coalesce(Sum(Case(When(destination_location=location,then=Abs(F("total_value"))),When(source_location=location,then=-Abs(F("total_value"))),default=Value(ZERO),output_field=DecimalField(max_digits=18,decimal_places=4))),ZERO,output_field=DecimalField()))["v"]
 return qs.aggregate(v=Coalesce(Sum(F("quantity_in")*F("unit_cost")-F("quantity_out")*F("unit_cost")),ZERO,output_field=DecimalField()))["v"]
