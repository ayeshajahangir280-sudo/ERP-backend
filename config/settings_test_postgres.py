"""PostgreSQL-only test settings. Never points at DATABASE_URL."""
from urllib.parse import urlparse
from .settings import *  # noqa: F403

test_database_url=env("TEST_DATABASE_URL",default="")  # noqa: F405
if not test_database_url:
    raise ImproperlyConfigured("TEST_DATABASE_URL is required for PostgreSQL tests.")  # noqa: F405
parsed=urlparse(test_database_url)
database_name=(parsed.path or "").lstrip("/").lower()
if parsed.scheme not in {"postgres","postgresql"}:
    raise ImproperlyConfigured("PostgreSQL concurrency tests require a postgresql:// TEST_DATABASE_URL.")  # noqa: F405
if "test" not in database_name or database_name in {"postgres","template0","template1"}:
    raise ImproperlyConfigured("Refusing unsafe TEST_DATABASE_URL: database name must unmistakably contain 'test'.")  # noqa: F405

DATABASES={"default":dj_database_url.parse(test_database_url,conn_max_age=0,conn_health_checks=True)}  # noqa: F405
# Django normally prefixes test databases. Use an explicit, still unmistakably
# test-only name so concurrent test workers never touch the configured database.
DATABASES["default"]["TEST"]={"NAME":f"test_{database_name}" if not database_name.startswith("test_") else database_name}
