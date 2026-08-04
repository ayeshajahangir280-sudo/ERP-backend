from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission,HasLocationAccess
from .models import SalesInvoice
from .serializers import SalesInvoiceSerializer
from .services import post_sale,cancel_sale
from rest_framework.decorators import action
from rest_framework.response import Response
class SalesInvoiceViewSet(AuditedModelViewSet):
 serializer_class=SalesInvoiceSerializer;permission_classes=[HasModulePermission,HasLocationAccess];module_name="sales"
 def get_queryset(self):
  q=SalesInvoice.objects.prefetch_related("items").order_by("-invoice_date");u=self.request.user
  return q if u.role=="ADMINISTRATOR" or u.can_access_all_locations or not u.assigned_location_id else q.filter(sales_location=u.assigned_location)
 @action(detail=True,methods=["post"])
 def post(self,request,pk=None):return Response({"success":True,"data":self.get_serializer(post_sale(pk,request.user)).data})
 @action(detail=True,methods=["post"])
 def cancel(self,request,pk=None):return Response({"success":True,"data":self.get_serializer(cancel_sale(pk,request.user,request.data.get("reason",""))).data})
