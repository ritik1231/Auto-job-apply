# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# gcc is needed to compile C extensions (e.g. asyncpg, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip --no-cache-dir

# Create a venv so the runtime stage gets a clean, relocatable install
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install only production dependencies (no [dev] extras)
COPY pyproject.toml ./
RUN pip install --no-cache-dir "."

# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Copy the pre-built venv — no compiler needed at runtime
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application source
COPY . .

# Create directories the app writes to at runtime
RUN chmod +x /app/start.sh \
    && mkdir -p storage/resumes secrets

# Non-root user for security
RUN useradd --no-create-home --system appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# wait-for-db.sh is the ENTRYPOINT for local docker-compose (waits for the
# postgres container). Set SKIP_DB_WAIT=true (e.g. on Render) to bypass it
# and go straight to start.sh, which runs migrations then starts the server.
ENTRYPOINT ["/app/scripts/wait-for-db.sh"]
CMD ["/app/start.sh"]
