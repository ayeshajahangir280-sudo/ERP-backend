from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission
from .models import Recipe
from .serializers import RecipeSerializer
class RecipeViewSet(AuditedModelViewSet):queryset=Recipe.objects.prefetch_related("items");serializer_class=RecipeSerializer;permission_classes=[HasModulePermission];module_name="recipes"
