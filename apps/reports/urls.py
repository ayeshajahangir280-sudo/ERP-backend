from django.urls import path
from .views import StockLedgerReport
urlpatterns=[path("reports/stock-ledger/",StockLedgerReport.as_view())]
