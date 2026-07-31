from decimal import Decimal
from django.db.models import Sum,Q,DecimalField
from django.db.models.functions import Coalesce
from .models import StockTransaction
ZERO=Decimal("0")
def _stock(qs): return qs.aggregate(v=Coalesce(Sum("quantity_in")-Sum("quantity_out"),ZERO,output_field=DecimalField()))["v"]
def get_raw_material_stock(material,location): return _stock(StockTransaction.objects.filter(raw_material=material).filter(Q(destination_location=location)|Q(source_location=location)))
def get_finished_product_stock(product,location,batch=None):
 qs=StockTransaction.objects.filter(finished_product=product).filter(Q(destination_location=location)|Q(source_location=location)); return _stock(qs.filter(batch=batch)) if batch is not None else _stock(qs)
def get_available_stock(item,location): return get_raw_material_stock(item,location) if item._meta.model_name=="rawmaterial" else get_finished_product_stock(item,location)
def get_stock_by_location(item):
 from apps.locations.models import Location
 return {str(x.id):get_available_stock(item,x) for x in Location.objects.filter(is_inventory_location=True)}
def get_inventory_valuation(location=None):
 qs=StockTransaction.objects.all()
 if location: qs=qs.filter(Q(destination_location=location)|Q(source_location=location))
 return qs.aggregate(v=Coalesce(Sum("total_value"),ZERO,output_field=DecimalField()))["v"]
