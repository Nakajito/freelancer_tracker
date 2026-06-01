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

python manage.py collectstatic --noinput

if [ "$SEED_DEMO" = "1" ]; then
    python manage.py seed_demo
fi

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -