#!/bin/bash
set -e

# Ensure the media directory is writable by the app user.
# When Coolify mounts a volume over /app/media the mount point is owned
# by root; this fixes ownership before we drop privileges.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/media
    chown -R app:app /app/media
    exec gosu app "$0" "$@"
fi

export PATH="/app/.venv/bin:$PATH"

python manage.py migrate --noinput

# No-op when REDIS_URL is set or the table already exists. Required for the
# DatabaseCache fallback that backs DRF throttling and allauth rate limits.
python manage.py createcachetable

python manage.py collectstatic --noinput

if [ "$SEED_DEMO" = "1" ]; then
    python manage.py seed_demo
fi

# Sync workers with no fronting buffer: without these caps a few slow or
# oversized requests can occupy every worker (slowloris), and workers never
# recycle, so leaked memory and stale state accumulate indefinitely.
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --limit-request-line 8190 \
    --limit-request-fields 100 \
    --limit-request-field_size 8190 \
    --access-logfile - \
    --error-logfile -