from rest_framework import generics,status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer,UserSerializer,ChangePasswordSerializer
from drf_spectacular.utils import OpenApiTypes,extend_schema,inline_serializer
from rest_framework import serializers
class LoginView(TokenObtainPairView): permission_classes=[AllowAny]; serializer_class=LoginSerializer
class MeView(APIView):
    @extend_schema(operation_id="auth_me",responses=UserSerializer)
    def get(self,request): return Response({"success":True,"data":UserSerializer(request.user).data})
class LogoutView(APIView):
    @extend_schema(operation_id="auth_logout",request=inline_serializer("LogoutRequest",fields={"refresh":serializers.CharField()}),responses={200:OpenApiTypes.OBJECT})
    def post(self,request):
        RefreshToken(request.data["refresh"]).blacklist(); return Response({"success":True,"message":"Logged out."})
class ChangePasswordView(generics.GenericAPIView):
    serializer_class=ChangePasswordSerializer
    def post(self,request):
        s=self.get_serializer(data=request.data); s.is_valid(raise_exception=True); request.user.set_password(s.validated_data["new_password"]); request.user.save(update_fields=["password"]); return Response({"success":True,"message":"Password changed."})
