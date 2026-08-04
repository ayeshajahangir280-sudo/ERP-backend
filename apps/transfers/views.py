from rest_framework.decorators import action
from rest_framework.response import Response
from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission
from .models import MaterialTransfer,FinishedGoodsTransfer
from .serializers import MaterialTransferSerializer,FinishedGoodsTransferSerializer
from .services import _transition,dispatch,receive
class BaseTransferViewSet(AuditedModelViewSet):
 permission_classes=[HasModulePermission];module_name="stock_transfers"
 @action(detail=True,methods=["post"])
 def submit(self,request,pk=None):return Response(self.get_serializer(_transition(self.get_object(),{"DRAFT"},"SUBMITTED",request.user)).data)
 @action(detail=True,methods=["post"])
 def approve(self,request,pk=None):return Response(self.get_serializer(_transition(self.get_object(),{"DRAFT","SUBMITTED"},"APPROVED",request.user,"approved_by" if hasattr(self.get_object(),"approved_by") else None)).data)
 @action(detail=True,methods=["post"])
 def dispatch(self,request,pk=None):return Response(self.get_serializer(dispatch(self.get_object(),request.user,isinstance(self.get_object(),FinishedGoodsTransfer))).data)
 @action(detail=True,methods=["post"])
 def receive(self,request,pk=None):return Response(self.get_serializer(receive(self.get_object(),request.user,request.data.get("items",[]),isinstance(self.get_object(),FinishedGoodsTransfer))).data)
class MaterialTransferViewSet(BaseTransferViewSet):queryset=MaterialTransfer.objects.prefetch_related("items");serializer_class=MaterialTransferSerializer;module_name="material_transfers"
class FinishedGoodsTransferViewSet(BaseTransferViewSet):queryset=FinishedGoodsTransfer.objects.prefetch_related("items");serializer_class=FinishedGoodsTransferSerializer
