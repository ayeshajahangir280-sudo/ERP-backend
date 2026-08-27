from .models import Location
from apps.master_data.serializers import ReactivatingSerializer

class LocationSerializer(ReactivatingSerializer):
 class Meta: model=Location; fields="__all__"; read_only_fields=("created_by","updated_by")
