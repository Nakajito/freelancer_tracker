#!/bin/bash
set -e

python manage.py migrate --noinput

if [ "$SEED_DEMO" = "1" ]; then
    python manage.py seed_demo
fi

exec "$@"