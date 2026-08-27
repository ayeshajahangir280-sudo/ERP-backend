from django.db import models as django_models
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from . import models


def _unique_field_sets(model):
 fields=[[field.name] for field in model._meta.fields if field.unique and not field.primary_key]
 fields.extend([list(entry) for entry in model._meta.unique_together])
 for constraint in model._meta.constraints:
  if isinstance(constraint, django_models.UniqueConstraint):
   fields.append(list(constraint.fields))
 return fields


class ReactivatingSerializer(serializers.ModelSerializer):
 def get_fields(self):
  fields=super().get_fields()
  for field in fields.values():
   field.validators=[validator for validator in field.validators if not isinstance(validator,UniqueValidator)]
  return fields
 def get_validators(self):
  return []
 def _status_filter(self,inactive):
  model=self.Meta.model
  names={field.name for field in model._meta.fields}
  if "status" in names:return {"status":"INACTIVE" if inactive else "ACTIVE"}
  if "is_active" in names:return {"is_active":False if inactive else True}
  return {}
 def _active_values(self,validated_data):
  names={field.name for field in self.Meta.model._meta.fields}
  data=dict(validated_data)
  if "status" in names:data["status"]="ACTIVE"
  if "is_active" in names:data["is_active"]=True
  return data
 def _matching_unique_record(self,validated_data,inactive):
  model=self.Meta.model
  for fields in _unique_field_sets(model):
   if not fields or not all(field in validated_data and validated_data[field] not in (None,"") for field in fields):
    continue
   filters={field:validated_data[field] for field in fields}
   filters.update(self._status_filter(inactive))
   existing=model.objects.filter(**filters).first()
   if existing:return existing
  return None
 def validate(self,attrs):
  if self.instance:
   return attrs
  active=self._matching_unique_record(attrs,False)
  if active:
   raise serializers.ValidationError("An active record with this unique value already exists.")
  return attrs
 def create(self,validated_data):
  existing=self._matching_unique_record(validated_data,True)
  if existing:
   for field,value in self._active_values(validated_data).items():
    setattr(existing,field,value)
   request=self.context.get("request")
   if request and hasattr(existing,"updated_by"):existing.updated_by=request.user
   existing.save()
   return existing
  return super().create(self._active_values(validated_data))


def make_serializer(model):
 meta=type("Meta",(),{"model":model,"fields":"__all__","read_only_fields":("created_by","updated_by")})
 return type(f"{model.__name__}Serializer",(ReactivatingSerializer,),{"Meta":meta,"__module__":__name__})
SupplierSerializer=make_serializer(models.Supplier); CustomerSerializer=make_serializer(models.Customer); UnitOfMeasurementSerializer=make_serializer(models.UnitOfMeasurement); TaxRateSerializer=make_serializer(models.TaxRate); PaymentMethodSerializer=make_serializer(models.PaymentMethod); RawMaterialSerializer=make_serializer(models.RawMaterial); FinishedProductSerializer=make_serializer(models.FinishedProduct); ShopProductSettingSerializer=make_serializer(models.ShopProductSetting)

class ItemCategorySerializer(ReactivatingSerializer):
 class Meta:
  model=models.ItemCategory;fields="__all__";read_only_fields=("created_by","updated_by")
