Plan: Despliegue freelancer_tracker en Coolify
Context
Proyecto Django 6 + uv ya tiene scaffolding parcial en deploy/ (Dockerfile multi-stage, docker-compose dev, entrypoint.sh). Objetivo: dejarlo listo para deploy en Coolify usando Dockerfile + Postgres gestionado por Coolify (Traefik termina TLS, sin docker-compose en prod, sin workers, sin seed demo).

Gaps actuales bloqueantes:

Bug crítico Dockerfile: línea 33 chmod +x /app/deploy/entrypoint.sh falla — deploy/ nunca se copia al runtime stage. Build rompe o entrypoint no existe.
No corre prod settings: DJANGO_SETTINGS_MODULE nunca se exporta. Defaultea a configuración insegura.
collectstatic en build sin SECRET_KEY: ManifestStaticFilesStorage requiere settings importables; build puede fallar o producir staticfiles incompleto.
Falta health endpoint: Coolify/Traefik necesita /healthz (o HEALTHCHECK Docker) para routing y rolling deploys.
CSRF_TRUSTED_ORIGINS ausente: Django 4+ rechaza POST detrás de proxy HTTPS sin esta config.
No-root user ausente: corre como root, riesgo seguridad.
.dockerignore ausente: build context incluye .venv, db.sqlite3, media/, tests, __pycache__.
Media volume: MEDIA_ROOT en /app/media se pierde sin volumen persistente declarado.
.env.example incompleto: falta SECURE_SSL_REDIRECT, CSRF_TRUSTED_ORIGINS, DJANGO_SETTINGS_MODULE, vars gunicorn.
gunicorn sin tunning: workers fijos, sin access log, sin timeout configurable.
Archivos a modificar
1. deploy/Dockerfile — reescribir
Cambios:

Builder stage: instalar uv vía pip, uv sync --frozen --no-dev → genera .venv.
Runtime stage: crear user app (uid 1000), WORKDIR /app, copiar .venv + código + deploy/ (incluye entrypoint).
Set ENV DJANGO_SETTINGS_MODULE=config.settings.prod y PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1.
Mover collectstatic a entrypoint (necesita env runtime), no a build.
chown -R app:app /app, USER app.
Añadir HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1 (instalar curl runtime, o usar Python urllib).
Copiar también manage.py, pyproject.toml (uv runtime usa metadata).
2. deploy/entrypoint.sh — extender
Pasos en orden:

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers ${GUNICORN_WORKERS:-3} \
  --timeout ${GUNICORN_TIMEOUT:-60} \
  --access-logfile - \
  --error-logfile -
Eliminar exec "$@" (fija comando explícito).

3. config/settings/prod.py — añadir
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
Mantener SECURE_PROXY_SSL_HEADER existente. SECURE_SSL_REDIRECT ya respeta env var → en Coolify ponerlo True (Traefik añade X-Forwarded-Proto).

4. config/urls.py + nuevo apps/core/views_health.py — health endpoint
Añadir vista mínima:

from django.http import JsonResponse
def healthz(request):
    return JsonResponse({"status": "ok"})
Registrar path("healthz", healthz) en config/urls.py antes del middleware de auth (ya es público por defecto). Reusar apps.core que ya existe.

5. Crear .dockerignore — nuevo
Excluir: .venv/, __pycache__/, *.pyc, db.sqlite3, media/, staticfiles/, .git/, .pytest_cache/, .mypy_cache/, .ruff_cache/, htmlcov/, .env, tests/, docs/, *.md (excepto README), node_modules/.

6. .env.example — extender
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com
DATABASE_URL=postgresql://USER:PASS@HOST:5432/DB
SECURE_SSL_REDIRECT=True
GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=60
SEED_DEMO=0
7. deploy/docker-compose.yml — dejar solo dev
Marcar como dev-only en comentario header. Coolify NO lo usará (modo Dockerfile). Mantener para docker compose up local.

8. Crear deploy/COOLIFY.md — nuevo
Pasos deploy Coolify:

Crear recurso PostgreSQL 16 en Coolify → copiar DATABASE_URL interno.
Crear app Dockerfile apuntando al repo, branch main, build context ., dockerfile path deploy/Dockerfile.
Settings → Storage → declarar volumen persistente /app/media.
Environment Variables → pegar todas las del .env.example con valores reales (DJANGO_SECRET_KEY generado con python -c 'import secrets;print(secrets.token_urlsafe(50))').
Domain → asignar dominio + activar HTTPS (Let's Encrypt automático).
Health Check Path → /healthz.
Port → 8000.
Deploy.
9. Hardening de ciberseguridad
9.1 Settings Django (prod.py)
Añadir / endurecer:

SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8        # 8h
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
Validar ALLOWED_HOSTS no vacío al arranque (fallar fuerte si lista vacía → evita host header injection).

9.2 Cabeceras adicionales — django-csp
Añadir dependencia django-csp a pyproject.toml. Middleware + CSP_DEFAULT_SRC = ("'self'",), permitir Tailwind compilado servido por whitenoise ('self'). Ajustar fuentes según assets reales.

9.3 Rate limiting login
Añadir django-axes (lockout + tracking IP). Config en prod.py: AXES_FAILURE_LIMIT=5, AXES_COOLOFF_TIME=1 hora, AXES_LOCKOUT_PARAMETERS=["username","ip_address"]. Backend en AUTHENTICATION_BACKENDS antes de allauth.

9.4 Secretos
DJANGO_SECRET_KEY ≥ 50 chars random, único por entorno, solo en Coolify Environment Variables (cifrado at-rest).
Nunca commitear .env (verificar .gitignore ya lo excluye).
Postgres password generado por Coolify, no reutilizar entre apps.
Rotar DJANGO_SECRET_KEY cada 90 días → invalidar sesiones aceptable.
9.5 Imagen Docker
Base python:3.14-slim → fijar digest SHA256 (python:3.14-slim@sha256:...) tras primer pin.
Runtime stage: solo libpq5 + curl (para HEALTHCHECK) → minimizar superficie.
Usuario app uid 1000 no-root (ya en sección 1).
read_only: true filesystem en docker-compose dev + tmpfs:/tmp (writable solo /app/media, /app/staticfiles).
No instalar gcc/dev tools en runtime stage (multi-stage ya lo evita; verificar).
9.6 Escaneo automático
Trivy scan imagen Docker + filesystem en CI.
pip-audit o safety sobre uv.lock → vulnerabilidades CVE en deps.
bandit SAST sobre apps/ y config/.
gitleaks scan secretos en repo.
Thresholds: fallar build si HIGH/CRITICAL.
9.7 Backups + DR
Coolify Postgres → activar backup automático diario, retención 7 días mínimo, off-site (S3/B2).
Volumen /app/media → snapshot semanal vía Coolify o cron restic/rclone.
Probar restore en staging trimestralmente.
9.8 Logging + auditoría
Logs gunicorn/Django → stdout (Coolify recoge). Activar django.security logger nivel WARNING.
Considerar django-auditlog si requiere trazabilidad de cambios en propuestas/clientes.
Sentry opcional → sentry-sdk[django], DSN vía env, scrubbing PII activado.
10. CI/CD — GitHub Actions
10.1 Crear .github/workflows/ci.yml
Triggers: push a main + dev, pull_request a main.

Jobs (paralelos donde aplique):

a) lint

Setup Python 3.14 + uv (astral-sh/setup-uv@v3).
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy apps config
uv run djlint templates --check
b) test

Service container postgres:16 con healthcheck.
uv sync --frozen
uv run pytest --cov=apps --cov-fail-under=85 --cov-report=xml
Upload coverage a Codecov (opcional).
Env: DATABASE_URL=postgres://postgres:postgres@localhost:5432/test, DJANGO_SETTINGS_MODULE=config.settings.test.
c) security

pip-audit -r <(uv export --no-hashes) o uv pip audit.
bandit -r apps config -ll.
gitleaks detect --source . --no-banner.
Fallar en HIGH/CRITICAL.
d) docker-build (depende de lint+test+security)

docker build -f deploy/Dockerfile -t freelancer-tracker:${{ github.sha }} .
trivy image --exit-code 1 --severity HIGH,CRITICAL freelancer-tracker:${{ github.sha }}
Push a GHCR ghcr.io/<owner>/freelancer-tracker:${{ github.sha }} + tag latest solo en main.
10.2 Crear .github/workflows/deploy.yml
Trigger: workflow_run de ci.yml exitoso en main, o push tag v*.

Job deploy-coolify:

Llamar webhook Coolify → secret COOLIFY_WEBHOOK_URL en GitHub Secrets.
curl -X POST "$COOLIFY_WEBHOOK_URL" -H "Authorization: Bearer $COOLIFY_TOKEN".
Coolify pull main + rebuild + rolling deploy con healthcheck /healthz.
10.3 Branch protection (configurar en GitHub UI)
main: require PR review, require status checks (lint, test, security, docker-build), no direct push, dismiss stale approvals on new commits, require linear history.
Signed commits opcional pero recomendado.
10.4 Dependabot — .github/dependabot.yml
Ecosystem pip (uv compatible vía pyproject.toml) semanal.
Ecosystem docker (base image) semanal.
Ecosystem github-actions semanal.
Auto-merge minor/patch tras CI verde (regla GitHub).
10.5 Pre-commit hooks — .pre-commit-config.yaml
Hooks: ruff, ruff-format, djlint, gitleaks, check-added-large-files, detect-private-key, end-of-file-fixer. Doc en README cómo instalar (uv run pre-commit install).

11. SEO + descubrimiento web
11.1 robots.txt
Servirlo dinámico para respetar DEBUG/dominio. Vista en apps/core/views_seo.py:

from django.http import HttpResponse
from django.views.decorators.cache import cache_page

@cache_page(60 * 60 * 24)
def robots_txt(request):
    host = request.get_host()
    body = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /accounts/\n"
        "Disallow: /api/\n"
        "Disallow: /healthz\n"
        "Disallow: /.well-known/\n"
        f"Sitemap: https://{host}/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain")
Registrar path("robots.txt", robots_txt) en config/urls.py.

11.2 Sitemap
Activar django.contrib.sitemaps en config/settings/base.py INSTALLED_APPS. Crear apps/core/sitemaps.py:

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return ["accounts:login", "accounts:signup"]   # solo páginas públicas

    def location(self, item):
        return reverse(item)
Registrar en config/urls.py:

from django.contrib.sitemaps.views import sitemap
from apps.core.sitemaps import StaticViewSitemap

sitemaps = {"static": StaticViewSitemap}
path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
Nota: app es SaaS multi-tenant con datos privados (propuestas, clientes, horas). NO incluir URLs autenticadas en sitemap. Solo landing + signup + login.

Configurar Site en admin (django.contrib.sites) con dominio real → sitemap usa Site.objects.get_current().

11.3 .well-known/
security.txt (RFC 9116) — divulgación coordinada de vulnerabilidades. Servir vía URL pattern + vista (no archivo estático para incluir fecha expiración dinámica):

@cache_page(60 * 60 * 24)
def security_txt(request):
    body = (
        "Contact: mailto:security@<dominio>\n"
        "Expires: 2027-05-10T00:00:00.000Z\n"
        "Preferred-Languages: es, en\n"
        "Canonical: https://<dominio>/.well-known/security.txt\n"
    )
    return HttpResponse(body, content_type="text/plain")
Registrar path(".well-known/security.txt", security_txt).

Otros .well-known posibles (omitir si no aplica):

change-password → redirect 302 a /accounts/password/change/ (estándar W3C).
apple-app-site-association / assetlinks.json → solo si hay app móvil (no aplica ahora).
acme-challenge/ → manejado por Coolify/Traefik automáticamente (Let's Encrypt). NO interferir.
Registrar:

from django.views.generic import RedirectView
path(".well-known/change-password", RedirectView.as_view(url="/accounts/password/change/", permanent=False)),
11.4 Whitenoise + .well-known
Whitenoise sirve STATIC_ROOT. Como rutas anteriores son vistas Django (no archivos), funcionan sin tocar whitenoise. Si se decide servir como archivos estáticos: colocar en static/.well-known/ + static/robots.txt y whitenoise los expone — pero vista dinámica preferida (dominio real, expiración security.txt).

11.5 Excluir de CSP / middleware auth
Vistas SEO públicas → asegurar no quedan tras auth middleware. URLs registradas a nivel raíz en config/urls.py ya son públicas (no bajo accounts/). Verificar LOGIN_REQUIRED_URLS (si se añade middleware global) excluya estos paths.

11.6 Cabeceras Coolify/Traefik
Confirmar Traefik no reescribe /.well-known/acme-challenge/ hacia la app (debe interceptar para renovación TLS). Coolify lo hace por defecto.

Verificación end-to-end
Local (antes de push):

docker build -f deploy/Dockerfile -t freelancer-tracker:test .
docker run --rm -e DJANGO_SECRET_KEY=test -e DEBUG=False \
  -e ALLOWED_HOSTS=localhost -e CSRF_TRUSTED_ORIGINS=http://localhost:8000 \
  -e DATABASE_URL=sqlite:///tmp/db.sqlite3 -e SECURE_SSL_REDIRECT=False \
  -p 8000:8000 freelancer-tracker:test
curl -f http://localhost:8000/healthz   # → {"status":"ok"}
Coolify (post-deploy):

https://<dominio>/healthz → 200 JSON
https://<dominio>/accounts/login/ → form renderiza, CSS Tailwind cargado vía whitenoise
Login + crear propuesta → persiste tras redeploy (verifica volumen /app/media + Postgres externo)
Logs Coolify muestran gunicorn + migrate exitosos sin tracebacks
docker exec al contenedor → whoami debe devolver app (no root)
Tests existentes:

uv run pytest --cov=apps --cov-fail-under=85
deben seguir pasando — cambios son aditivos en infra, no tocan apps.

Verificación seguridad post-deploy:

curl -I https://<dominio> → headers Strict-Transport-Security, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Content-Security-Policy, Referrer-Policy: same-origin.
https://securityheaders.com/?q=<dominio> → grade A o superior.
https://www.ssllabs.com/ssltest/analyze.html?d=<dominio> → grade A.
Probar 6 logins fallidos consecutivos → axes lockea cuenta + IP.
Verificar cookies en DevTools: Secure, HttpOnly, SameSite=Lax.
docker exec contenedor → id debe ser uid 1000, no root.
Revisar logs Coolify: sin tracebacks, sin warnings de SECURE_*.
Verificación SEO + .well-known:

curl https://<dominio>/robots.txt → contenido con Sitemap: apuntando dominio real, sin Disallow: / global.
curl https://<dominio>/sitemap.xml → XML válido, solo URLs públicas (login/signup), <loc> con https://.
curl https://<dominio>/.well-known/security.txt → cabeceras Contact, Expires futuro, Canonical correcto.
curl -I https://<dominio>/.well-known/change-password → 302 redirect a /accounts/password/change/.
Google Search Console → submit sitemap.xml, verificar 0 errores cobertura.
https://internet.nl/site/<dominio>/ → grade A (TLS + headers + DNSSEC).
Verificar Let's Encrypt renueva sin tocar acme-challenge/ (logs Coolify/Traefik).
Verificación CI/CD:

Abrir PR ficticio → los 4 jobs (lint/test/security/docker-build) corren y pasan.
Merge a main → workflow deploy.yml dispara webhook → Coolify rebuild visible en UI.
Probar PR con vulnerabilidad sembrada (ej. dep antigua) → security job falla y bloquea merge.