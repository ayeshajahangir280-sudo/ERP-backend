from rest_framework.viewsets import ModelViewSet
from django.db.models.deletion import ProtectedError, RestrictedError


class AuditedModelViewSet(ModelViewSet):
    def perform_create(self,serializer): serializer.save(created_by=self.request.user,updated_by=self.request.user)
    def perform_update(self,serializer): serializer.save(updated_by=self.request.user)
    def perform_destroy(self,instance):
        try:
            instance.delete()
        except (ProtectedError,RestrictedError):
            # Preserve foreign-key history without blocking the user's delete.
            # Archived rows remain available to existing related records, while
            # API clients treat them as removed from active lists.
            fields={field.name for field in instance._meta.fields}
            if "is_active" in fields:
                instance.is_active=False
                update_fields=["is_active"]
            elif "status" in fields:
                instance.status="INACTIVE"
                update_fields=["status"]
            else:
                raise
            if "updated_by" in fields:
                instance.updated_by=self.request.user
                update_fields.append("updated_by")
            if "updated_at" in fields:
                update_fields.append("updated_at")
            instance.save(update_fields=update_fields)
