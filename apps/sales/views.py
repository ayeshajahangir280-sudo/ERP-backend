from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission,HasLocationAccess
from .models import SalesInvoice
from .serializers import SalesInvoiceSerializer
class SalesInvoiceViewSet(AuditedModelViewSet):
 serializer_class=SalesInvoiceSerializer;permission_classes=[HasModulePermission,HasLocationAccess];module_name="sales"
 def get_queryset(self):
  q=SalesInvoice.objects.prefetch_related("items").order_by("-invoice_date");u=self.request.user
  return q if u.role=="ADMINISTRATOR" or u.can_access_all_locations or not u.assigned_location_id else q.filter(sales_location=u.assigned_location)
