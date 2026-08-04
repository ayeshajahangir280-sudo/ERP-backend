from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from apps.accounts.permissions import IsAdministrator
from django.apps import apps
from common.viewsets import hard_delete_instance

from .models import ERPState


class ERPStateView(APIView):
    def get(self, request):
        state = ERPState.objects.filter(key="default").first()
        if state is None:
            return Response({"data": None, "revision": 0})
        return Response({"data": state.data, "revision": state.revision})

    @transaction.atomic
    def put(self, request):
        data = request.data.get("data")
        if not isinstance(data, dict):
            return Response({"detail": "data must be a JSON object"}, status=400)

        state, _ = ERPState.objects.select_for_update().get_or_create(key="default")
        state.data = data
        state.revision += 1
        state.updated_by = request.user
        state.save(update_fields=["data", "revision", "updated_by", "updated_at"])
        return Response({"revision": state.revision, "updated_at": state.updated_at})


class DeleteAllDataView(APIView):
    permission_classes = [IsAdministrator]

    @transaction.atomic
    def post(self, request):
        """Remove all ERP business data while preserving the signed-in admin."""
        empty_state = request.data.get("data")
        if not isinstance(empty_state, dict):
            return Response({"detail": "data must be a JSON object"}, status=status.HTTP_400_BAD_REQUEST)

        keep_user = request.user
        app_labels = {
            "locations", "master_data", "inventory", "purchasing", "recipes",
            "production", "transfers", "sales", "payments", "audit", "reports",
            "system_state",
        }
        seen = set()
        for model in (m for m in apps.get_models() if m._meta.app_label in app_labels):
            for instance in list(model._base_manager.all()):
                hard_delete_instance(instance, seen)

        keep_user.__class__.objects.exclude(pk=keep_user.pk).delete()
        ERPState.objects.create(key="default", data=empty_state, revision=1, updated_by=keep_user)
        return Response({"success": True, "message": "All system data was deleted. The main administrator was preserved."})
