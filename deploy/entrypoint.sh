#!/bin/bash
set -e

export PATH="/app/.venv/bin:$PATH"

python manage.py migrate --noinput

bin/build-css.sh

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