#!/bin/sh
set -e

# External managed databases may still be starting when Dokploy launches the
# container. Retry migrations briefly instead of failing the first deployment.
attempt=1
until python manage.py migrate --noinput; do
  if [ "$attempt" -ge 10 ]; then
    echo "Database migration failed after $attempt attempts."
    exit 1
  fi
  echo "Database unavailable; retrying migration in 3 seconds ($attempt/10)."
  attempt=$((attempt + 1))
  sleep 3
done

python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile - \
  --preload
