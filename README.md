# BakeryFlow ERP Backend

Standalone Django REST Framework backend for the existing Lovable frontend. It uses JWT authentication, explicit per-user module assignments, location-scoped data access, PostgreSQL, and an immutable stock ledger.

## Setup

Copy `.env.example` to `.env` and replace `DATABASE_URL` with the PostgreSQL URL you provide. Never commit `.env`.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Docker: `copy .env.example .env`, then run `docker compose up --build`.

Tests and validation:

```powershell
python manage.py check
python manage.py test
```

## Authentication and access

- `POST /api/auth/login/` with `email` and `password`
- `POST /api/auth/refresh/`, `POST /api/auth/logout/`
- `GET /api/auth/me/` returns role, assigned location, and `allowed_modules`
- `POST /api/auth/change-password/`

Administrators see all modules and locations. Other users must have the API's module in `allowed_modules`; users without `can_access_all_locations` are restricted to `assigned_location`. This is enforced server-side.

Demo accounts use `DEMO_PASSWORD` (development default `BakeryFlow2026!`): admin, purchase, production, warehouse, shop1, shop2, accounts, and manager at `@bakeryflow.local`.

Swagger: `/api/docs/`; ReDoc: `/api/redoc/`; schema: `/api/schema/`.

## Frontend integration

Set `VITE_API_BASE_URL=http://localhost:8000/api`. Send `Authorization: Bearer <access>` on API requests, refresh with the refresh token after a 401, and build navigation from `allowed_modules` returned by `/auth/me/`. API errors use `{success, message, errors}`. Transaction actions use endpoints such as `POST /purchases/{id}/post/` and `/cancel/`.

Stock transactions are read-only via the API and are created only by atomic domain services. Posted records are reversed rather than deleted.

## Current extension points

The schema includes production, transfers, sales returns, and payment allocations. Their more advanced posting/action services and additional analytical report endpoints can be expanded as the frontend switches from its local store to API calls. Celery and Redis configuration is ready but workers are not required for startup.
