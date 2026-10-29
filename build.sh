#!/usr/bin/env bash
# Build script for hosts like Render: installs deps, builds the React app,
# collects static files and applies migrations.
set -o errexit

pip install -r requirements.txt

cd frontend
npm ci
# CI=false keeps existing lint warnings from failing the build
CI=false npm run build
cd ..

cd mistyrose
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Create/restore the demo account and sample posts (set SEED_DEMO=false to skip).
# Needs the site's public URL: $SITE_URL, or Render's $RENDER_EXTERNAL_URL.
if [ "${SEED_DEMO:-true}" = "true" ]; then
  python manage.py seed_demo || echo "seed_demo failed (see the message above); continuing without demo data."
fi

# Create the admin account on first deploy if credentials are provided
# (DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input || echo "Superuser already exists, skipping."
fi
