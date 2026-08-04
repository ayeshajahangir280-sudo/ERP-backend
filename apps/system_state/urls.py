from django.urls import path

from .views import DeleteAllDataView, ERPStateView

urlpatterns = [
    path("erp-state/", ERPStateView.as_view(), name="erp-state"),
    path("system/delete-all-data/", DeleteAllDataView.as_view(), name="delete-all-data"),
]
