from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
class LoginSerializer(TokenObtainPairSerializer):
    username_field="email"
    def validate(self,attrs):
        data=super().validate(attrs); data["user"]=UserSerializer(self.user).data; return data
class UserSerializer(serializers.ModelSerializer):
    class Meta: model=User; fields=("id","email","full_name","employee_code","role","department","assigned_location","can_access_all_locations","allowed_modules","is_active")
class ChangePasswordSerializer(serializers.Serializer):
    old_password=serializers.CharField(); new_password=serializers.CharField(min_length=8)
    def validate_old_password(self,v):
        if not self.context["request"].user.check_password(v): raise serializers.ValidationError("Current password is incorrect.")
        return v
