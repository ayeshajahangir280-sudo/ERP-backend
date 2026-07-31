from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import HasModulePermission
from apps.inventory.models import StockTransaction
from apps.inventory.serializers import StockTransactionSerializer
class StockLedgerReport(APIView):
 permission_classes=[HasModulePermission];module_name="reports"
 def get(self,request):
  q=StockTransaction.objects.all().order_by("-transaction_date")
  for key in ("transaction_type","raw_material","finished_product"):
   if request.query_params.get(key):q=q.filter(**{key:request.query_params[key]})
  return Response({"success":True,"data":StockTransactionSerializer(q[:1000],many=True).data})
