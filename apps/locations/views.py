from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission
from .models import Location
from .serializers import LocationSerializer
class LocationViewSet(AuditedModelViewSet):
 queryset=Location.objects.all(); serializer_class=LocationSerializer; permission_classes=[HasModulePermission]; module_name="inventory"; search_fields=["code","name"]; filterset_fields=["location_type","is_active"]
