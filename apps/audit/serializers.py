from rest_framework.serializers import ModelSerializer
from .models import AuditLog
class AuditLogSerializer(ModelSerializer):
 class Meta:model=AuditLog;fields="__all__";read_only_fields=fields
