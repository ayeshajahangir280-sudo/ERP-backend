from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiTypes,extend_schema,inline_serializer
from rest_framework import serializers

from apps.accounts.permissions import IsAdministrator
from apps.audit.models import AuditLog
from apps.inventory.models import InventoryBalance,StockAdjustment,StockTransaction,WastageDocument
from apps.locations.models import Location
from apps.master_data.models import Customer,FinishedProduct,ItemCategory,PaymentMethod,RawMaterial,ShopProductSetting,Supplier,TaxRate,UnitOfMeasurement
from apps.payments.models import CustomerPayment,CustomerPaymentAllocation,SupplierPayment,SupplierPaymentAllocation
from apps.production.models import ProductionBatch,ProductionConsumption,ProductionOutput,ProductionWastage
from apps.purchasing.models import PurchaseInvoice,PurchaseInvoiceItem,SupplierLedger
from apps.recipes.models import Recipe,RecipeItem
from apps.reports.models import ReportExportJob
from apps.sales.models import CustomerLedger,SalesInvoice,SalesInvoiceItem,SalesReturn,SalesReturnItem
from apps.transfers.models import FinishedGoodsTransfer,FinishedGoodsTransferItem,MaterialTransfer,MaterialTransferItem

from .models import ERPState
from .models import IdempotencyRecord

ERP_STATE_ALLOWED_KEYS=frozenset({"uiPreferences"})
ERP_STATE_TRANSACTIONAL_KEYS=frozenset({
    "purchaseInvoices","productionBatches","openingStocks","stockAdjustments","wastages","materialTransfers","stockTransfers",
    "salesInvoices","salesReturns","customerPayments","supplierPayments","stockLedger","inventoryBalances","customerBalances",
    "supplierBalances","reports","dashboard","counters",
})
ERP_STATE_FORBIDDEN_NORMALIZED={"".join(ch for ch in key.lower() if ch.isalnum()) for key in ERP_STATE_TRANSACTIONAL_KEYS}|{"stock","ledger","invoice","payment","purchase","production","transfer","return","wastage","adjustment","balance","report","dashboard"}

def validate_ui_preferences(value,path="uiPreferences"):
    if isinstance(value,list):return f"{path} cannot contain arrays."
    if isinstance(value,dict):
        for key,nested in value.items():
            normalized="".join(ch for ch in str(key).lower() if ch.isalnum())
            if any(token in normalized for token in ERP_STATE_FORBIDDEN_NORMALIZED):return f"{path}.{key} resembles transactional data and is not allowed."
            error=validate_ui_preferences(nested,f"{path}.{key}")
            if error:return error
        return None
    if value is None or isinstance(value,(str,int,float,bool)):return None
    return f"{path} contains an unsupported value."

class ERPStateView(APIView):
    permission_classes=[IsAuthenticated]

    @extend_schema(operation_id="erp_state_retrieve",responses=OpenApiTypes.OBJECT)
    def get(self, request):
        state = ERPState.objects.filter(key="default").first()
        if state is None:
            return Response({"data": None, "revision": 0})
        safe_data={key:state.data[key] for key in ERP_STATE_ALLOWED_KEYS if key in state.data}
        return Response({"data": safe_data, "revision": state.revision})

    @transaction.atomic
    @extend_schema(operation_id="erp_state_update",request=inline_serializer("ERPStateUpdateRequest",fields={"data":serializers.JSONField(),"revision":serializers.IntegerField()}),responses=OpenApiTypes.OBJECT)
    def put(self, request):
        data = request.data.get("data")
        expected_revision = request.data.get("revision")
        if not isinstance(data, dict):
            return Response({"detail": "data must be a JSON object"}, status=400)
        if expected_revision is None:
            return Response({"detail": "revision is required for optimistic locking"}, status=400)
        rejected=sorted(set(data)-ERP_STATE_ALLOWED_KEYS)
        if rejected:
            return Response({"detail":"ERPState only accepts prototype/UI snapshot data. Normalized transactional data must use its backend API.","rejected_keys":rejected,"allowed_keys":sorted(ERP_STATE_ALLOWED_KEYS)},status=400)
        if "uiPreferences" in data:
            error=validate_ui_preferences(data["uiPreferences"])
            if error:return Response({"detail":error},status=400)

        state, created = ERPState.objects.select_for_update().get_or_create(key="default")
        if created:
            state.revision = 0
        if int(expected_revision) != state.revision:
            return Response({"detail": "ERP state is stale. Refresh before saving.", "revision": state.revision}, status=409)
        state.data = {key:data[key] for key in ERP_STATE_ALLOWED_KEYS if key in data}
        state.revision += 1
        state.updated_by = request.user
        state.save(update_fields=["data", "revision", "updated_by", "updated_at"])
        return Response({"revision": state.revision, "updated_at": state.updated_at})

def delete_model(model,counts):
    label=model._meta.label
    count=model.objects.count()
    if count:
        model.objects.all().delete()
    counts[label]=count

def raw_delete_model(model,counts):
    label=model._meta.label
    queryset=model.objects.all()
    count=queryset.count()
    if count:
        queryset._raw_delete(queryset.db)
    counts[label]=count

class ClearBusinessDataView(APIView):
    permission_classes=[IsAdministrator]

    @transaction.atomic
    @extend_schema(operation_id="business_data_clear",responses=OpenApiTypes.OBJECT)
    def post(self,request):
        counts={}
        for model in (
            CustomerPaymentAllocation,
            SupplierPaymentAllocation,
            CustomerPayment,
            SupplierPayment,
            SalesReturnItem,
            SalesReturn,
            CustomerLedger,
            SalesInvoiceItem,
            SalesInvoice,
            SupplierLedger,
            PurchaseInvoiceItem,
            PurchaseInvoice,
            ProductionWastage,
            ProductionOutput,
            ProductionConsumption,
            ProductionBatch,
            MaterialTransferItem,
            FinishedGoodsTransferItem,
            MaterialTransfer,
            FinishedGoodsTransfer,
            StockAdjustment,
            WastageDocument,
            InventoryBalance,
        ):
            delete_model(model,counts)
        raw_delete_model(StockTransaction,counts)
        for model in (
            RecipeItem,
            Recipe,
            ShopProductSetting,
            RawMaterial,
            FinishedProduct,
            ItemCategory,
            Supplier,
            Customer,
            PaymentMethod,
            TaxRate,
            UnitOfMeasurement,
            Location,
            ReportExportJob,
            IdempotencyRecord,
            ERPState,
            AuditLog,
        ):
            delete_model(model,counts)
        return Response({"success":True,"message":"Business/testing data cleared.","deleted":counts})
