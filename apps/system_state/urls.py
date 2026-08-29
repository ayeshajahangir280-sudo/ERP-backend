from django.urls import path

from .views import ERPStateView,ClearBusinessDataView

urlpatterns = [
    path("erp-state/", ERPStateView.as_view(), name="erp-state"),
    path("system/clear-business-data/", ClearBusinessDataView.as_view(), name="clear-business-data"),
]
