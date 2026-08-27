from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import Recipe,RecipeItem
class RecipeItemSerializer(serializers.ModelSerializer):
 class Meta:model=RecipeItem;exclude=("recipe",)
class RecipeSerializer(serializers.ModelSerializer):
 items=RecipeItemSerializer(many=True);total_material_cost=serializers.DecimalField(max_digits=18,decimal_places=4,read_only=True);cost_per_output_unit=serializers.DecimalField(max_digits=18,decimal_places=4,read_only=True)
 class Meta:model=Recipe;fields="__all__";read_only_fields=("created_by","updated_by")
 def get_fields(self):
  fields=super().get_fields()
  fields["recipe_number"].validators=[validator for validator in fields["recipe_number"].validators if not isinstance(validator,UniqueValidator)]
  return fields
 def validate(self,data):
  if self.instance:return data
  existing=Recipe.objects.filter(recipe_number=data.get("recipe_number"),status="ACTIVE").first()
  if existing:raise serializers.ValidationError("An active recipe with this number already exists.")
  return data
 @transaction.atomic
 def create(self,data):
  items=data.pop("items",[])
  if not items:raise serializers.ValidationError("A recipe requires at least one material.")
  # A new active default version replaces the previous default for the product.
  # Clear it first so the conditional unique constraint never produces an HTML 500 page.
  if data.get("is_default") and data.get("status") == "ACTIVE":
   Recipe.objects.filter(
    finished_product=data.get("finished_product"),is_default=True,status="ACTIVE"
   ).update(is_default=False)
  obj=Recipe.objects.filter(recipe_number=data.get("recipe_number"),status="INACTIVE").first()
  if obj:
   for field,value in data.items():setattr(obj,field,value)
   obj.status="ACTIVE"
   obj.items.all().delete()
   request=self.context.get("request")
   if request:obj.updated_by=request.user
   obj.save()
  else:
   obj=Recipe.objects.create(**data)
  for i in items:RecipeItem.objects.create(recipe=obj,**i)
  return obj
 @transaction.atomic
 def update(self,instance,data):
  items=data.pop("items",None)
  if data.get("is_default") and data.get("status",instance.status) == "ACTIVE":
   Recipe.objects.filter(finished_product=data.get("finished_product",instance.finished_product),is_default=True,status="ACTIVE").exclude(pk=instance.pk).update(is_default=False)
  obj=super().update(instance,data)
  if items is not None:
   obj.items.all().delete()
   for i in items:RecipeItem.objects.create(recipe=obj,**i)
  return obj
