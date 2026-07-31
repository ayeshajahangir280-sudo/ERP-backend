from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission
from .models import ProductionBatch
from .serializers import ProductionBatchSerializer
class ProductionBatchViewSet(AuditedModelViewSet):queryset=ProductionBatch.objects.all();serializer_class=ProductionBatchSerializer;permission_classes=[HasModulePermission];module_name="production"
