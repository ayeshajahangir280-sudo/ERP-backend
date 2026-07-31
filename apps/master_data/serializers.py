from rest_framework import serializers
from . import models
def make_serializer(model):
 class S(serializers.ModelSerializer):
  class Meta: fields="__all__"; read_only_fields=("created_by","updated_by")
 S.Meta.model=model; return S
SupplierSerializer=make_serializer(models.Supplier); CustomerSerializer=make_serializer(models.Customer); ItemCategorySerializer=make_serializer(models.ItemCategory); UnitOfMeasurementSerializer=make_serializer(models.UnitOfMeasurement); TaxRateSerializer=make_serializer(models.TaxRate); PaymentMethodSerializer=make_serializer(models.PaymentMethod); RawMaterialSerializer=make_serializer(models.RawMaterial); FinishedProductSerializer=make_serializer(models.FinishedProduct); ShopProductSettingSerializer=make_serializer(models.ShopProductSetting)
