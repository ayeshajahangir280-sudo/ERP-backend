from rest_framework import serializers
from .models import SalesInvoice,SalesInvoiceItem,SalesReturn
class SalesItemSerializer(serializers.ModelSerializer):
 class Meta:model=SalesInvoiceItem;exclude=("sales_invoice",);read_only_fields=("unit_cost_snapshot","tax_amount","line_total","cost_total","gross_profit")
class SalesInvoiceSerializer(serializers.ModelSerializer):
 items=SalesItemSerializer(many=True)
 class Meta:model=SalesInvoice;fields="__all__";read_only_fields=("status","subtotal","discount_total","vat_total","grand_total","cost_of_goods_sold","gross_profit","gross_margin_percentage","paid_amount","outstanding_amount","created_by","updated_by")
 def create(self,data):
  items=data.pop("items",[]);obj=SalesInvoice.objects.create(**data)
  for i in items:SalesInvoiceItem.objects.create(sales_invoice=obj,**i)
  return obj
