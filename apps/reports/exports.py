import csv, os, tempfile
from decimal import Decimal
from uuid import UUID
from types import SimpleNamespace

from django.core.files import File
from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook

from apps.audit.models import AuditLog
from .models import ReportExportJob
from .views import DocumentReport,InventoryReport,ProductionReport,PurchaseReport,ReconciliationReport,ReturnsPaymentsReport,SalesReport,StockLedgerReport

REPORTS={}
for names,view in [(("raw-material-stock","production-stock","finished-goods-stock","stock-by-location","inventory-valuation"),InventoryReport),(("stock-ledger","stock-movement","item-movement-history"),StockLedgerReport),(("wastage","adjustments"),DocumentReport),(("purchase-register","supplier-ledger","supplier-outstanding","purchases-by-item"),PurchaseReport),(("production-register","material-consumption","production-cost","production-efficiency"),ProductionReport),(("sales-register","customer-ledger","customer-outstanding","sales-by-product","sales-by-customer","sales-by-branch","daily-sales","monthly-sales","gross-profit"),SalesReport),(("sales-returns","return-analysis","customer-return-history","customer-payments","supplier-payments"),ReturnsPaymentsReport),(("reconciliation",),ReconciliationReport)]:
 for name in names:REPORTS[name]=view

def excel_value(value):
 if isinstance(value,(UUID,Decimal)):return str(value)
 return value

def report_rows(job):
 request=SimpleNamespace(user=job.requested_by,query_params=job.filters)
 view=REPORTS[job.report_name](report_name=job.report_name)
 return iter(view.rows(request))

def process_export(job_id):
 with transaction.atomic():
  job=ReportExportJob.objects.select_for_update().select_related("requested_by").get(pk=job_id)
  if job.status not in {"PENDING","FAILED"}:return job
  job.status="RUNNING";job.attempts+=1;job.started_at=timezone.now();job.error="";job.save(update_fields=["status","attempts","started_at","error"])
 path=None
 try:
  rows=report_rows(job);first=next(rows,None);columns=list(first.keys()) if first else []
  suffix=".xlsx" if job.output_format=="XLSX" else ".csv"
  fd,path=tempfile.mkstemp(suffix=suffix);os.close(fd)
  if job.output_format=="XLSX":
   book=Workbook(write_only=True);sheet=book.create_sheet("Report");sheet.append(columns)
   if first:sheet.append([excel_value(first.get(c)) for c in columns])
   for row in rows:sheet.append([excel_value(row.get(c)) for c in columns])
   book.save(path)
  else:
   with open(path,"w",newline="",encoding="utf-8-sig") as target:
    writer=csv.DictWriter(target,fieldnames=columns);writer.writeheader()
    if first:writer.writerow(first)
    writer.writerows(rows)
  with open(path,"rb") as source:job.file.save(f"{job.report_name}-{job.id}{suffix}",File(source),save=False)
  job.status="COMPLETED";job.completed_at=timezone.now();job.save(update_fields=["file","status","completed_at"])
  AuditLog.objects.create(user=job.requested_by,action="Export",module="reports",record_type="ReportExportJob",record_id=job.id,record_number=str(job.id),description=f"Completed {job.report_name} {job.output_format} export",new_values={"filters":job.filters,"format":job.output_format})
 except Exception as exc:
  job.status="FAILED";job.error=str(exc)[:2000];job.completed_at=timezone.now();job.save(update_fields=["status","error","completed_at"]);raise
 finally:
  if path and os.path.exists(path):os.unlink(path)
 return job
