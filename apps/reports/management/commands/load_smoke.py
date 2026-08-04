import json, statistics, time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.inventory.models import InventoryBalance, StockTransaction
from apps.purchasing.models import PurchaseInvoice
from apps.sales.models import SalesInvoice


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument("--users",type=int,default=4);parser.add_argument("--iterations",type=int,default=25);parser.add_argument("--output",required=True)
    def handle(self,*args,**options):
        database=settings.DATABASES["default"]
        host=(database.get("HOST") or "").lower();name=(database.get("NAME") or "").lower()
        if any(token in host or token in name for token in ("prod","production","live")):raise CommandError("Refusing to run against a production-looking database.")
        def request(_):
            close_old_connections();started=time.perf_counter()
            list(InventoryBalance.objects.values_list("id","current_quantity","inventory_value")[:100]);StockTransaction.objects.order_by("-transaction_date").values_list("id",flat=True).first();SalesInvoice.objects.count();PurchaseInvoice.objects.count()
            elapsed=(time.perf_counter()-started)*1000;close_old_connections();return elapsed
        count=options["users"]*options["iterations"];started=time.perf_counter()
        with ThreadPoolExecutor(max_workers=options["users"]) as pool:latencies=list(pool.map(request,range(count)))
        ordered=sorted(latencies);percentile=lambda p:ordered[min(len(ordered)-1,int(len(ordered)*p))]
        result={"dataset":{"balances":InventoryBalance.objects.count(),"stock_transactions":StockTransaction.objects.count()},"concurrency":options["users"],"requests":count,"duration_seconds":round(time.perf_counter()-started,3),"throughput_rps":round(count/max(time.perf_counter()-started,.001),2),"average_ms":round(statistics.mean(latencies),2),"p95_ms":round(percentile(.95),2),"p99_ms":round(percentile(.99),2),"error_rate":0}
        with open(options["output"],"w",encoding="utf-8") as target:json.dump(result,target,indent=2)
        self.stdout.write(json.dumps(result))
