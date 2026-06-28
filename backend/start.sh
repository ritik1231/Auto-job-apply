#!/bin/sh
# Production entrypoint: run database migrations then start the API server.
# Render injects $PORT; defaults to 8000 for local Docker runs.
set -e

echo "[start] Running database migrations..."
alembic upgrade head

echo "[start] Starting server on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1
