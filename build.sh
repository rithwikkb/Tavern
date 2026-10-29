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

# Create the admin account on first deploy if credentials are provided
# (DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input || echo "Superuser already exists, skipping."
fi
