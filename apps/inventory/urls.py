from rest_framework.routers import DefaultRouter
from .views import StockTransactionViewSet
r=DefaultRouter();r.register("inventory/stock-transactions",StockTransactionViewSet,basename="stock-transaction");urlpatterns=r.urls
