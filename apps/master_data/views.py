from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission
from django.db.models.deletion import ProtectedError, RestrictedError
from . import models,serializers
def make_view(model,serializer,module):
 class V(AuditedModelViewSet):
  queryset=model.objects.all(); serializer_class=serializer; permission_classes=[HasModulePermission]; module_name=module; ordering_fields="__all__"
 return V
SupplierViewSet=make_view(models.Supplier,serializers.SupplierSerializer,"suppliers"); CustomerViewSet=make_view(models.Customer,serializers.CustomerSerializer,"customers")

class ItemCategoryViewSet(AuditedModelViewSet):
 queryset=models.ItemCategory.objects.all(); serializer_class=serializers.ItemCategorySerializer; permission_classes=[HasModulePermission]; module_name="settings"; ordering_fields="__all__"
 def perform_destroy(self, instance):
  try:
   instance.delete()
  except (ProtectedError, RestrictedError):
   # Keep the row as a historical lookup for products/materials that already
   # reference it, while removing it from active category management.
   instance.status="INACTIVE"; instance.updated_by=self.request.user; instance.save(update_fields=["status","updated_by","updated_at"])

UnitViewSet=make_view(models.UnitOfMeasurement,serializers.UnitOfMeasurementSerializer,"settings"); TaxRateViewSet=make_view(models.TaxRate,serializers.TaxRateSerializer,"settings"); PaymentMethodViewSet=make_view(models.PaymentMethod,serializers.PaymentMethodSerializer,"settings"); RawMaterialViewSet=make_view(models.RawMaterial,serializers.RawMaterialSerializer,"raw_materials"); FinishedProductViewSet=make_view(models.FinishedProduct,serializers.FinishedProductSerializer,"finished_goods"); ShopProductSettingViewSet=make_view(models.ShopProductSetting,serializers.ShopProductSettingSerializer,"inventory")
