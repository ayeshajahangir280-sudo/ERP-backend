from rest_framework.serializers import ModelSerializer
from .models import ProductionBatch
class ProductionBatchSerializer(ModelSerializer):
 class Meta:model=ProductionBatch;fields="__all__";read_only_fields=("status","recipe_version","material_cost","total_production_cost","cost_per_unit","posted_at","posted_by","created_by","updated_by")
