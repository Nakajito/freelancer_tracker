FROM python:3.14-slim AS builder

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 app \
    && useradd -m -u 1000 -g app app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY --from=builder /app/pyproject.toml /app/uv.lock ./
COPY apps/ ./apps/
COPY config/ ./config/
COPY templates/ ./templates/
COPY static/ ./static/
COPY manage.py ./
COPY deploy/entrypoint.sh ./

RUN chmod +x entrypoint.sh

RUN chown -R app:app /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

ENTRYPOINT ["./entrypoint.sh"]