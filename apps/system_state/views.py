from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

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

