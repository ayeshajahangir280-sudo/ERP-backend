from rest_framework.viewsets import ReadOnlyModelViewSet
from django.db import models
from apps.accounts.permissions import HasModulePermission
from .models import StockTransaction
from .serializers import StockTransactionSerializer
class StockTransactionViewSet(ReadOnlyModelViewSet):
 serializer_class=StockTransactionSerializer; permission_classes=[HasModulePermission]; module_name="inventory"; filterset_fields=["transaction_type","raw_material","finished_product","source_location","destination_location","batch"]
 def get_queryset(self):
  qs=StockTransaction.objects.all().order_by("-transaction_date"); u=self.request.user
  if u.role!="ADMINISTRATOR" and not u.can_access_all_locations and u.assigned_location_id: qs=qs.filter(models.Q(source_location=u.assigned_location)|models.Q(destination_location=u.assigned_location))
  return qs
