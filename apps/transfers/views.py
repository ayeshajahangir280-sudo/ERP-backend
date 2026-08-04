from rest_framework.decorators import action
from rest_framework.response import Response
from common.viewsets import AuditedModelViewSet
from apps.accounts.permissions import HasModulePermission
from .models import MaterialTransfer,FinishedGoodsTransfer
from .serializers import MaterialTransferSerializer,FinishedGoodsTransferSerializer
from .services import _transition,dispatch,receive,cancel_transfer
from common.idempotency import idempotent_action
from apps.inventory.document_services import generated_number
class BaseTransferViewSet(AuditedModelViewSet):
 permission_classes=[HasModulePermission];module_name="stock_transfers"
 def perform_create(self,serializer):serializer.save(transfer_number=generated_number("TRF"),created_by=self.request.user,updated_by=self.request.user)
 @action(detail=True,methods=["post"])
 def submit(self,request,pk=None):return Response(self.get_serializer(_transition(self.get_object(),{"DRAFT"},"SUBMITTED",request.user)).data)
 @action(detail=True,methods=["post"])
 def approve(self,request,pk=None):return Response(self.get_serializer(_transition(self.get_object(),{"DRAFT","SUBMITTED"},"APPROVED",request.user,"approved_by" if hasattr(self.get_object(),"approved_by") else None)).data)
 @action(detail=True,methods=["post"])
 @idempotent_action
 def dispatch(self,request,pk=None):return Response(self.get_serializer(dispatch(self.get_object(),request.user,isinstance(self.get_object(),FinishedGoodsTransfer))).data)
 @action(detail=True,methods=["post"])
 @idempotent_action
 def receive(self,request,pk=None):return Response(self.get_serializer(receive(self.get_object(),request.user,request.data.get("items",[]),isinstance(self.get_object(),FinishedGoodsTransfer))).data)
 @action(detail=True,methods=["post"])
 @idempotent_action
 def cancel(self,request,pk=None):return Response(self.get_serializer(cancel_transfer(self.get_object(),request.user,request.data.get("reason",""))).data)
class MaterialTransferViewSet(BaseTransferViewSet):queryset=MaterialTransfer.objects.prefetch_related("items");serializer_class=MaterialTransferSerializer;module_name="material_transfers"
class FinishedGoodsTransferViewSet(BaseTransferViewSet):queryset=FinishedGoodsTransfer.objects.prefetch_related("items");serializer_class=FinishedGoodsTransferSerializer
