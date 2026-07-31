from rest_framework import serializers
from .models import StockTransaction
class StockTransactionSerializer(serializers.ModelSerializer):
 class Meta: model=StockTransaction; fields="__all__"; read_only_fields=fields
