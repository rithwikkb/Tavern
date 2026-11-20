# Tavern as one container: the React frontend is built in a Node stage, and only the built
# files are copied into a slim Python image that runs Django with gunicorn.

# ---- 1. Build the frontend ----
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
# dependencies first, so they're cached until package*.json changes
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=dev --no-audit --no-fund
COPY frontend/ ./
RUN GENERATE_SOURCEMAP=false npm run build

# ---- 2. The app ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY mistyrose/ ./mistyrose/
COPY --from=frontend /app/frontend/build ./frontend/build
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

WORKDIR /app/mistyrose
# Static files are part of the image. The key only exists for this step (settings refuse to
# load without one) and isn't kept in the image. Then switch to an unprivileged user, which
# only needs to write here for the SQLite file (used when there's no DATABASE_URL).
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --no-input \
    && useradd --create-home --uid 10001 tavern \
    && chown -R tavern:tavern /app/mistyrose
USER tavern

EXPOSE 8000
# /healthz/ answers without touching the database (and over plain http)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/healthz/', timeout=4)"

ENTRYPOINT ["entrypoint.sh"]
