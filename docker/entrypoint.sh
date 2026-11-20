#!/bin/sh
# Container start-up: bring the database up to date, optionally load the demo data, then
# hand over to gunicorn (exec, so it receives stop signals directly).
set -e

python manage.py migrate --no-input

if [ "${SEED_DEMO:-false}" = "true" ]; then
  python manage.py seed_demo
fi

exec gunicorn mistyrose.wsgi \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads 4 \
  --timeout 60
