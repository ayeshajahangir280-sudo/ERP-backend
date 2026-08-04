import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from django.db import models, transaction
from django.db.models import Case, DecimalField, F, Sum, Value, When
from apps.accounts.permissions import HasModulePermission
from .models import StockTransaction
from .serializers import StockTransactionSerializer
class StockTransactionViewSet(ReadOnlyModelViewSet):
 serializer_class=StockTransactionSerializer; permission_classes=[HasModulePermission]; module_name="inventory"; filterset_fields=["transaction_type","raw_material","finished_product","source_location","destination_location"]
 def get_queryset(self):
  qs=StockTransaction.objects.all().order_by("-transaction_date"); u=self.request.user
  if u.role!="ADMINISTRATOR" and not u.can_access_all_locations and u.assigned_location_id: qs=qs.filter(models.Q(source_location=u.assigned_location)|models.Q(destination_location=u.assigned_location))
  return qs
 @action(detail=False,methods=["get"],url_path="balances")
 def balances(self,request):
  """Return one current balance per item and location; historical batches are ignored."""
  balances={}
  for entry in self.get_queryset().select_related("unit"):
   item_type="RM" if entry.raw_material_id else "FG"
   item_id=entry.raw_material_id or entry.finished_product_id
   movements=[]
   if entry.destination_location_id and entry.quantity_in:
    movements.append((entry.destination_location_id,entry.quantity_in,abs(entry.total_value)))
   if entry.source_location_id and entry.quantity_out:
    movements.append((entry.source_location_id,-entry.quantity_out,-abs(entry.total_value)))
   for location_id,quantity,value in movements:
    key=(item_type,item_id,location_id)
    current=balances.setdefault(key,{"item_type":item_type,"item_id":str(item_id),"location_id":str(location_id),"quantity":Decimal("0"),"value":Decimal("0"),"unit":str(entry.unit_id)})
    current["quantity"]+=quantity;current["value"]+=value
  data=[]
  for current in balances.values():
   quantity=current["quantity"]
   current["average_cost"]=current["value"]/quantity if quantity>0 else Decimal("0")
   data.append(current)
  return Response({"success":True,"data":data})
 @action(detail=False,methods=["post"],url_path="opening-finished-goods")
 def opening_finished_goods(self,request):
  from apps.locations.models import Location
  from apps.master_data.models import FinishedProduct
  try:
   product=FinishedProduct.objects.get(pk=request.data.get("finished_product"),status="ACTIVE")
   location=Location.objects.get(pk=request.data.get("location"),location_type="FINISHED_GOODS_WAREHOUSE",is_active=True)
   quantity=Decimal(str(request.data.get("quantity",0)))
   expiry=str(request.data.get("expiry_date","")).strip()
   if quantity<=0: raise ValueError
  except (FinishedProduct.DoesNotExist,Location.DoesNotExist,ValueError,TypeError):
   return Response({"success":False,"message":"A valid product, finished-goods location and positive quantity are required."},status=status.HTTP_400_BAD_REQUEST)
  reference_id=uuid.uuid4()
  transaction=StockTransaction.objects.create(
   transaction_number=f"OPEN-FG-{reference_id}",transaction_date=timezone.now(),
   transaction_type="STOCK_ADJUSTMENT_IN",reference_type="OpeningFinishedGoods",reference_id=reference_id,
   finished_product=product,batch="",destination_location=location,quantity_in=quantity,
   unit=product.sales_unit,unit_cost=product.standard_cost,total_value=quantity*product.standard_cost,
   remarks=f"Opening / externally produced finished goods|EXPIRY={expiry}",created_by=request.user,
  )
  return Response({"success":True,"message":"Existing finished goods added.","data":self.get_serializer(transaction).data},status=status.HTTP_201_CREATED)
 @action(detail=False,methods=["post"],url_path="adjust")
 @transaction.atomic
 def adjust(self,request):
  from apps.locations.models import Location
  from apps.master_data.models import FinishedProduct,RawMaterial
  from .services import get_available_stock,get_average_cost
  item_type=str(request.data.get("item_type","")).upper()
  model=RawMaterial if item_type=="RM" else FinishedProduct if item_type=="FG" else None
  try:
   if model is None: raise ValueError
   item=model.objects.select_for_update().get(pk=request.data.get("item"),status="ACTIVE")
   location=Location.objects.get(pk=request.data.get("location"),is_active=True)
   quantity=Decimal(str(request.data.get("quantity",0)))
   reason=str(request.data.get("reason","")).strip()
   if not quantity or not reason: raise ValueError
  except (RawMaterial.DoesNotExist,FinishedProduct.DoesNotExist,Location.DoesNotExist,ValueError,TypeError):
   return Response({"success":False,"message":"A valid active item, location, non-zero quantity and reason are required."},status=status.HTTP_400_BAD_REQUEST)
  available=get_available_stock(item,location)
  if quantity<0 and -quantity>available:
   return Response({"success":False,"message":f"Insufficient stock. Only {available} is available at this location."},status=status.HTTP_400_BAD_REQUEST)
  unit_cost=get_average_cost(item,location)
  if quantity>0 and request.data.get("unit_cost") not in (None,""):
   unit_cost=Decimal(str(request.data["unit_cost"]))
   if unit_cost<0:
    return Response({"success":False,"message":"Unit cost cannot be negative."},status=status.HTTP_400_BAD_REQUEST)
  reference_id=uuid.uuid4();incoming=quantity>0
  fields={"raw_material":item} if item_type=="RM" else {"finished_product":item}
  entry=StockTransaction.objects.create(
   transaction_number=f"ADJ-{reference_id}",transaction_date=timezone.now(),
   transaction_type="STOCK_ADJUSTMENT_IN" if incoming else "STOCK_ADJUSTMENT_OUT",
   reference_type="StockAdjustment",reference_id=reference_id,batch="",
   destination_location=location if incoming else None,source_location=None if incoming else location,
   quantity_in=quantity if incoming else Decimal("0"),quantity_out=Decimal("0") if incoming else -quantity,
   unit=item.base_unit if item_type=="RM" else item.sales_unit,unit_cost=unit_cost,
   total_value=abs(quantity)*unit_cost,remarks=reason,created_by=request.user,**fields,
  )
  return Response({"success":True,"data":self.get_serializer(entry).data},status=status.HTTP_201_CREATED)
 @action(detail=False,methods=["post"],url_path="clear-finished-goods")
 def clear_finished_goods(self,request):
  from apps.locations.models import Location
  from apps.master_data.models import FinishedProduct
  try:
   product=FinishedProduct.objects.get(pk=request.data.get("finished_product"))
   location=Location.objects.get(pk=request.data.get("location"),is_active=True)
   reason=str(request.data.get("reason","")).strip() or "Removed from finished-goods inventory"
  except (FinishedProduct.DoesNotExist,Location.DoesNotExist,ValueError,TypeError):
   return Response({"success":False,"message":"A valid product and location are required."},status=status.HTTP_400_BAD_REQUEST)
  transactions=StockTransaction.objects.filter(finished_product=product).filter(
   models.Q(destination_location=location)|models.Q(source_location=location)
  )
  totals=transactions.aggregate(
   quantity=Sum(F("quantity_in")-F("quantity_out"),default=Decimal("0")),
   value=Sum(Case(
    When(destination_location=location,then=F("total_value")),
    When(source_location=location,then=-F("total_value")),
    default=Value(Decimal("0")),output_field=DecimalField(max_digits=18,decimal_places=4),
   ),default=Decimal("0")),
  )
  quantity=totals["quantity"] or Decimal("0")
  if quantity<=0:
   return Response({"success":False,"message":"This inventory row has no available stock to remove."},status=status.HTTP_400_BAD_REQUEST)
  unit_cost=(totals["value"] or Decimal("0"))/quantity
  reference_id=uuid.uuid4()
  transaction=StockTransaction.objects.create(
   transaction_number=f"CLEAR-FG-{reference_id}",transaction_date=timezone.now(),
   transaction_type="STOCK_ADJUSTMENT_OUT",reference_type="ClearFinishedGoods",reference_id=reference_id,
   finished_product=product,batch="",source_location=location,quantity_out=quantity,
   unit=product.sales_unit,unit_cost=unit_cost,total_value=quantity*unit_cost,
   remarks=f"Inventory row removed: {reason}",created_by=request.user,
  )
  return Response({"success":True,"message":"Finished-goods inventory row removed.","data":self.get_serializer(transaction).data},status=status.HTTP_201_CREATED)
 @action(detail=False,methods=["post"],url_path="opening-raw-material")
 def opening_raw_material(self,request):
  from apps.locations.models import Location
  from apps.master_data.models import RawMaterial
  try:
   material=RawMaterial.objects.get(pk=request.data.get("raw_material"),status="ACTIVE")
   location=Location.objects.get(pk=request.data.get("location"),location_type="RAW_MATERIAL_WAREHOUSE",is_active=True)
   quantity=Decimal(str(request.data.get("quantity",0)))
   if quantity<=0: raise ValueError
  except (RawMaterial.DoesNotExist,Location.DoesNotExist,ValueError,TypeError):
   return Response({"success":False,"message":"A valid raw material, raw-material warehouse and positive quantity are required."},status=status.HTTP_400_BAD_REQUEST)
  reference_id=uuid.uuid4()
  transaction=StockTransaction.objects.create(
   transaction_number=f"OPEN-RM-{reference_id}",transaction_date=timezone.now(),
   transaction_type="STOCK_ADJUSTMENT_IN",reference_type="OpeningRawMaterial",reference_id=reference_id,
   raw_material=material,destination_location=location,quantity_in=quantity,
   unit=material.base_unit,unit_cost=material.current_average_cost,total_value=quantity*material.current_average_cost,
   remarks="Opening raw-material stock",created_by=request.user,
  )
  return Response({"success":True,"message":"Opening raw-material stock added.","data":self.get_serializer(transaction).data},status=status.HTTP_201_CREATED)
