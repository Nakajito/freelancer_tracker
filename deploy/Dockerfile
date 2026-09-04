FROM python:3.14-slim AS builder

RUN pip install --no-cache-dir "uv==0.9.28"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    gettext \
    gosu \
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
COPY locale/ ./locale/
COPY src/ ./src/
COPY manage.py ./
COPY bin/ ./bin/
COPY deploy/entrypoint.sh ./

# The Tailwind binary is downloaded and executed at build time. Pin the
# version and verify its digest instead of trusting whatever the URL serves.
ARG TAILWIND_VERSION=v4.3.0
ARG TAILWIND_SHA256
RUN chmod +x entrypoint.sh \
    && curl -fsSL "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-x64" \
       -o /usr/local/bin/tailwindcss \
    && if [ -n "${TAILWIND_SHA256}" ]; then \
         echo "${TAILWIND_SHA256}  /usr/local/bin/tailwindcss" | sha256sum -c -; \
       fi \
    && chmod +x /usr/local/bin/tailwindcss \
    && bin/build-css.sh \
    && rm /usr/local/bin/tailwindcss \
    && DJANGO_SETTINGS_MODULE=config.settings.prod \
       DJANGO_SECRET_KEY=build-time-only-never-used-at-runtime-padding-0000 \
       ALLOWED_HOSTS=localhost \
       EMAIL_HOST_USER=build EMAIL_HOST_PASSWORD=build \
       .venv/bin/python manage.py compilemessages --ignore=.venv

RUN chown -R app:app /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# The entrypoint re-execs via gosu after fixing a mounted volume's ownership.
# Declaring USER here means `docker exec`, an overridden --entrypoint and the
# HEALTHCHECK all run unprivileged rather than as root.
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

ENTRYPOINT ["./entrypoint.sh"]