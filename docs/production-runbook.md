# BakeryFlow production runbook

## Environments and workflows

Use separate PostgreSQL databases and secrets for CI, staging, and production. GitHub workflows use temporary service containers only and never accept production database URLs. Run `postgresql-tests.yml`, `query-plans.yml`, `backup-restore.yml`, and `load-smoke.yml` from GitHub Actions before release. The frontend repository must pass `frontend-checks.yml`.

In Dokploy, set `DATABASE_URL` to the PostgreSQL service's internal hostname, not `localhost` and not its public endpoint. Required variables are `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `TIME_ZONE`, and `REDIS_URL`. Store them in Dokploy secrets and rotate immediately after suspected exposure.

## Deployment

1. Create and verify an off-server backup.
2. Run `python manage.py audit_payment_migration_data --fail-on-error`.
3. Run `python manage.py check --deploy` and `python manage.py makemigrations --check --dry-run`.
4. Put application workers into drain mode, then run `python manage.py migrate --noinput` once.
5. Start web and worker processes, check `/api/health/`, then perform the staging QA checklist.
6. Run inventory and financial fingerprints/reconciliation and compare dashboard totals with reports.

Use Gunicorn with bounded request timeouts and multiple workers. Run the export/idempotency cleanup commands from a scheduled worker. Put a connection pool such as PgBouncer in transaction mode between the application and PostgreSQL when connection concurrency requires it.

## Backup and restore

Take daily custom-format backups with `pg_dump -Fc`, retain daily copies for 14 days and monthly copies for 12 months, encrypt them, and copy them off-server. Test restoration monthly.

Restore only into an empty database:

```sh
createdb bakeryflow_restore
pg_restore --no-owner --exit-on-error -d bakeryflow_restore bakeryflow.dump
DATABASE_URL=postgresql://USER:PASSWORD@INTERNAL_HOST/bakeryflow_restore python manage.py check
DATABASE_URL=postgresql://USER:PASSWORD@INTERNAL_HOST/bakeryflow_restore python manage.py migrate --check
DATABASE_URL=postgresql://USER:PASSWORD@INTERNAL_HOST/bakeryflow_restore python manage.py database_fingerprint --output restored.json
```

Never place real credentials in commands committed to Git. Switch application traffic only after counts, outstanding balances, inventory values, and reconciliation match.

## Rollback

Stop new writes, retain the failed database, deploy the previous application image, and restore the pre-deployment backup when a migration changed data incompatibly. Do not blindly reverse transactional migrations after new documents have posted. Record the incident and exact recovery point.

## Monitoring and security

Monitor health checks, HTTP 5xx/409 rates, worker failures, slow queries, lock waits, database connections, replication/backup age, disk usage, memory, and reconciliation discrepancies. Alert on negative balance attempts and failed exports. Apply API rate limits at the ingress, use TLS, restrict allowed hosts/CORS/CSRF origins, use least-privilege database accounts, and rotate application/database secrets on a defined schedule.

## Staging QA and launch checklist

- Verify administrator, manager, restricted-location, and unauthorized users.
- Post and cancel purchases, production, sales, transfers/receipts, returns, wastage, adjustments, opening stock, and both payment types.
- Exercise partial/damaged receipts and partial/multi-invoice allocations.
- Verify duplicate submissions replay safely and conflicting keys return 409.
- Confirm deactivated masters disappear while historical documents and ledgers remain.
- Compare every dashboard KPI with its report and database fingerprint.
- Run PostgreSQL races, query plans, backup/restore, load smoke, and full staging load tests.
- Confirm logs contain no secrets and backups restore off-server.
