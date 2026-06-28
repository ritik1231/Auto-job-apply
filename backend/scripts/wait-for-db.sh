#!/bin/sh
# wait-for-db.sh — block until PostgreSQL accepts TCP connections, then exec CMD.
#
# Env vars:
#   DB_HOST         hostname to probe   (default: db)
#   DB_PORT         port to probe       (default: 5432)
#   DB_MAX_RETRIES  retry attempts      (default: 30)
#   SKIP_DB_WAIT    set to "true" to bypass the wait (e.g. in unit-test containers)
#
# Usage (as ENTRYPOINT):
#   ENTRYPOINT ["/app/scripts/wait-for-db.sh"]
#   CMD ["uvicorn", "app.main:app", ...]
set -e

if [ "${SKIP_DB_WAIT:-}" = "true" ]; then
    echo "[wait-for-db] SKIP_DB_WAIT=true — bypassing DB wait."
    exec "$@"
fi

export DB_HOST="${DB_HOST:-db}"
export DB_PORT="${DB_PORT:-5432}"
export DB_MAX_RETRIES="${DB_MAX_RETRIES:-30}"

echo "[wait-for-db] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} (max ${DB_MAX_RETRIES}s)..."

# Use Python's socket module — always available in the Python base image.
python - <<'PYEOF'
import socket, sys, time, os

host     = os.environ["DB_HOST"]
port     = int(os.environ["DB_PORT"])
retries  = int(os.environ["DB_MAX_RETRIES"])

for attempt in range(1, retries + 1):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"[wait-for-db] PostgreSQL is ready (attempt {attempt}).", flush=True)
            sys.exit(0)
    except OSError:
        print(f"[wait-for-db] Attempt {attempt}/{retries} — not ready yet.", flush=True)
        time.sleep(1)

print("[wait-for-db] ERROR: PostgreSQL did not become available. Exiting.", file=sys.stderr)
sys.exit(1)
PYEOF

echo "[wait-for-db] Starting application..."
exec "$@"
