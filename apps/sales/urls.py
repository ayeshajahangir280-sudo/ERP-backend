from rest_framework.routers import DefaultRouter
from .views import SalesInvoiceViewSet
r=DefaultRouter();r.register("sales-invoices",SalesInvoiceViewSet,basename="sales-invoice");urlpatterns=r.urls
