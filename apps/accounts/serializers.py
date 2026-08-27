from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

ROLE_MODULES={
 "PURCHASE":["dashboard","purchasing","suppliers","supplier_payments","raw_materials","reports"],
 "PRODUCTION":["dashboard","material_transfers","recipes","production","wastage","finished_goods","reports"],
 "WAREHOUSE":["dashboard","raw_materials","inventory","stock_adjustments","material_transfers","finished_goods","stock_transfers","reports"],
 "SALES":["dashboard","stock_transfers","sales","customers","customer_payments","sales_returns","reports"],
 "ACCOUNTS":["dashboard","purchasing","suppliers","supplier_payments","customers","customer_payments","reports"],
 "MANAGER":[x[0] for x in User.MODULES if x[0] not in ("users","settings")],
 "ADMINISTRATOR":[x[0] for x in User.MODULES],
}

def default_modules_for_role(role):
    return ROLE_MODULES.get(role,[])

class LoginSerializer(TokenObtainPairSerializer):
    username_field="email"
    def validate(self,attrs):
        identifier=(attrs.get("email") or "").strip()
        if identifier and "@" not in identifier:
            user=User.objects.filter(employee_code__iexact=identifier).first()
            if user:
                attrs["email"]=user.email
        data=super().validate(attrs); data["user"]=UserSerializer(self.user).data; return data
class UserSerializer(serializers.ModelSerializer):
    class Meta: model=User; fields=("id","email","full_name","employee_code","role","department","assigned_location","can_access_all_locations","allowed_modules","is_active")
class UserAdminSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True,required=False,min_length=8)
    class Meta:
        model=User
        fields=("id","email","full_name","employee_code","role","department","assigned_location","can_access_all_locations","allowed_modules","is_active","password")
        read_only_fields=("id",)
    def create(self,validated_data):
        password=validated_data.pop("password",None)
        if not validated_data.get("allowed_modules"):
            validated_data["allowed_modules"]=default_modules_for_role(validated_data.get("role"))
        if validated_data.get("role")=="ADMINISTRATOR":
            validated_data["can_access_all_locations"]=True
            validated_data["is_staff"]=True
        return User.objects.create_user(password=password,**validated_data)
    def update(self,instance,validated_data):
        password=validated_data.pop("password",None)
        if "role" in validated_data and not validated_data.get("allowed_modules",instance.allowed_modules):
            validated_data["allowed_modules"]=default_modules_for_role(validated_data["role"])
        for key,value in validated_data.items():setattr(instance,key,value)
        if password:instance.set_password(password)
        instance.save()
        return instance
class ResetUserPasswordSerializer(serializers.Serializer):
    password=serializers.CharField(min_length=8)
class ChangePasswordSerializer(serializers.Serializer):
    old_password=serializers.CharField(); new_password=serializers.CharField(min_length=8)
    def validate_old_password(self,v):
        if not self.context["request"].user.check_password(v): raise serializers.ValidationError("Current password is incorrect.")
        return v
