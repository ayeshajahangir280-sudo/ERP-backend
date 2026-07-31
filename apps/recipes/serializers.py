from rest_framework import serializers
from .models import Recipe,RecipeItem
class RecipeItemSerializer(serializers.ModelSerializer):
 class Meta:model=RecipeItem;exclude=("recipe",)
class RecipeSerializer(serializers.ModelSerializer):
 items=RecipeItemSerializer(many=True);total_material_cost=serializers.DecimalField(max_digits=18,decimal_places=4,read_only=True);cost_per_output_unit=serializers.DecimalField(max_digits=18,decimal_places=4,read_only=True)
 class Meta:model=Recipe;fields="__all__";read_only_fields=("created_by","updated_by")
 def create(self,data):
  items=data.pop("items",[])
  if not items:raise serializers.ValidationError("A recipe requires at least one material.")
  obj=Recipe.objects.create(**data)
  for i in items:RecipeItem.objects.create(recipe=obj,**i)
  return obj
