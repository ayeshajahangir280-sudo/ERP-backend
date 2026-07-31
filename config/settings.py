from pathlib import Path
from datetime import timedelta
import environ, dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DJANGO_DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-development-only-key")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
# The API is intentionally reachable through localhost, LAN addresses, tunnels,
# and deployed frontend hosts. Tighten these settings before a public rollout.
ALLOWED_HOSTS = ["*"]
DATABASES = {"default": dj_database_url.config(default=env("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"), conn_max_age=600)}
INSTALLED_APPS = [
 "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
 "corsheaders","rest_framework","rest_framework_simplejwt.token_blacklist","django_filters","drf_spectacular",
 "apps.accounts","apps.locations","apps.master_data","apps.inventory","apps.purchasing","apps.recipes","apps.production","apps.transfers","apps.sales","apps.payments","apps.audit","apps.reports",
]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","corsheaders.middleware.CorsMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware"]
ROOT_URLCONF="config.urls"; WSGI_APPLICATION="config.wsgi.application"; ASGI_APPLICATION="config.asgi.application"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
AUTH_USER_MODEL="accounts.User"
LANGUAGE_CODE="en-us"; TIME_ZONE=env("TIME_ZONE",default="Asia/Dubai"); USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; STATIC_ROOT=BASE_DIR/"staticfiles"; MEDIA_URL="media/"; MEDIA_ROOT=BASE_DIR/"media"; DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
CORS_ALLOW_ALL_ORIGINS=env.bool("CORS_ALLOW_ALL_ORIGINS",default=True)
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
USE_X_FORWARDED_HOST=True
# API authentication is JWT-only, so DRF endpoints do not use cookie/session
# authentication and are not subject to CSRF validation.
CSRF_TRUSTED_ORIGINS=env.list("CSRF_TRUSTED_ORIGINS",default=[])
REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES":["rest_framework_simplejwt.authentication.JWTAuthentication"],"DEFAULT_PERMISSION_CLASSES":["rest_framework.permissions.IsAuthenticated"],"DEFAULT_FILTER_BACKENDS":["django_filters.rest_framework.DjangoFilterBackend","rest_framework.filters.SearchFilter","rest_framework.filters.OrderingFilter"],"DEFAULT_PAGINATION_CLASS":"common.pagination.StandardPagination","PAGE_SIZE":25,"DEFAULT_SCHEMA_CLASS":"drf_spectacular.openapi.AutoSchema","EXCEPTION_HANDLER":"common.exceptions.api_exception_handler"}
SIMPLE_JWT={"ACCESS_TOKEN_LIFETIME":timedelta(minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES",default=60)),"REFRESH_TOKEN_LIFETIME":timedelta(days=env.int("REFRESH_TOKEN_LIFETIME_DAYS",default=7)),"ROTATE_REFRESH_TOKENS":True,"BLACKLIST_AFTER_ROTATION":True}
SPECTACULAR_SETTINGS={"TITLE":"BakeryFlow ERP API","VERSION":"1.0.0","SERVE_INCLUDE_SCHEMA":False}
CELERY_BROKER_URL=env("REDIS_URL",default="redis://localhost:6379/0"); CELERY_TASK_ALWAYS_EAGER=False
