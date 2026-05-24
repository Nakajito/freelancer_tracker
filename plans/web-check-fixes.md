# Plan: Solventar recomendaciones web-check.xyz para pipelancer.dabg.dev

## Context

Auditoría de https://web-check.xyz/check/pipelancer.dabg.dev arrojó:

- **Performance 0.57** — LCP/FCP en 8.9s. Causa raíz: render-blocking de Tailwind CDN (130 KiB JS que compila CSS en runtime), htmx CDN, Google Fonts. La fuente `Material Symbols Outlined` pesa 1.1 MiB (~82% del payload total de 1.3 MiB).
- **Accesibilidad** — La página de aterrizaje (`templates/dashboard/landing.html`) extiende `base.html` directamente. `base.html` no envuelve `{% block content %}` en `<main>`. (`app_base.html:112` y `auth_base.html` sí tienen `<main>`).
- **SEO** — Falta `<meta name="description">`. robots.txt servido por Cloudflare añade `Content-Signal: search=yes,ai-train=no` (línea 29 según lighthouse) — directiva no estándar marcada como error.
- **Seguridad** — No hay header CSP. `apps/core/views_seo.py:36` emite `mailto:security@` (email roto, sin dominio).
- **Caching** — Activos `/static/*` se sirven con `max-age=14400` (4h) — Cloudflare lo está limitando, WhiteNoise está bien configurado con `CompressedManifestStaticFilesStorage`.

Objetivo: LCP < 2.5s, accesibilidad 100, SEO sin avisos críticos, CSP activo.

Decisiones de diseño confirmadas con usuario:
- Tailwind: CLI standalone (`pytailwindcss`), sin Node.
- Material Symbols: self-host con subset.
- Geist + Inter: self-host con subset Latin.
- Cloudflare: incluir checklist ops separado.

---

## Cambios por archivo

### 1. Frontend build pipeline (Tailwind sin CDN)

**Nuevo: `pyproject.toml`** — añadir `pytailwindcss` a deps de desarrollo (genera binario `tailwindcss` en PATH).

**Nuevo: `tailwind.config.js`** (en raíz del repo, no en static)
- Migrar tokens de tema actualmente en `static/js/tailwind.config.js` (M3 colors, font families, spacing scale).
- `content`: `["templates/**/*.html", "apps/**/templates/**/*.html"]` para purge.
- Plugins: `@tailwindcss/forms`, `@tailwindcss/container-queries` (ya pip-instalables vía pytailwindcss).

**Nuevo: `static/css/src/app.css`**
```
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Nuevo: `bin/build-css.sh`**
```sh
#!/usr/bin/env bash
set -euo pipefail
tailwindcss -i static/css/src/app.css -o static/css/app.css --minify
```

**Modificar: `deploy/Dockerfile`** — antes de `collectstatic` (entrypoint línea 8):
```
RUN bin/build-css.sh
```
(Asegurar `pytailwindcss` instalado en imagen — viene por uv sync si está en pyproject.)

**Eliminar tras migrar:** `static/js/tailwind.config.js` (ya no se carga en runtime).

---

### 2. Self-host htmx + iconos + fuentes

**Nuevo: `static/vendor/htmx-1.9.10.min.js`** — descargar de https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js, commitear.

**Iconos: `static/fonts/material-symbols/`**
- Detectar iconos usados: `grep -roh "material-symbols-outlined[^>]*>[[:space:]]*[a-z_]\+" templates/ apps/ | sort -u` y extraer nombre.
- Generar subset .woff2 con [glyphhanger](https://github.com/zachleat/glyphhanger) o servicio web https://google-webfonts-helper.herokuapp.com con lista filtrada.
- Tamaño objetivo: < 50 KiB.
- Reemplazar `static/css/icons.css` por `@font-face` apuntando a archivo local + clase `.material-symbols-outlined` con `font-family`, `font-feature-settings: 'liga'`.

**Fuentes Geist + Inter: `static/fonts/geist/`, `static/fonts/inter/`**
- Descargar woff2 subset Latin de google-webfonts-helper.
- Geist: pesos 400, 500, 600, 700, 800, 900.
- Inter: 400, 500, 600.
- Añadir `@font-face` en `static/css/src/fonts.css`, importar desde `app.css`.
- Usar `font-display: swap`.

---

### 3. Refactor `templates/base.html`

Reemplazar líneas 13-26 con:

```html
<meta name="description" content="{% block meta_description %}PropoTrack — track freelance proposals, follow-ups, time entries, and revenue in one place.{% endblock %}">

<link rel="preload" href="{% static 'fonts/geist/geist-v4-latin-700.woff2' %}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{% static 'fonts/inter/inter-v20-latin-400.woff2' %}" as="font" type="font/woff2" crossorigin>

<link rel="stylesheet" href="{% static 'css/app.css' %}">
<link rel="stylesheet" href="{% static 'css/forms.css' %}">
<link rel="stylesheet" href="{% static 'css/htmx.css' %}">
<link rel="icon" type="image/x-icon" href="{% static 'favicon.ico' %}">
{% block extra_css %}{% endblock %}
```

Mover scripts justo antes de `</body>` con `defer`:
```html
<script src="{% static 'vendor/htmx-1.9.10.min.js' %}" defer></script>
{% block extra_js %}{% endblock %}
```

Envolver el contenido en `<main>`:
```html
<body ...>
  {% block body %}
    {# messages block #}
    <main>
      {% block content %}{% endblock %}
    </main>
  {% endblock %}
</body>
```

Nota: `app_base.html` y `auth_base.html` ya emiten su propio `<main>` y NO usan `{% block content %}` directamente (ver `app_base.html:127` `app_content`, no choca). Verificar en revisión que no se anidan dos `<main>`.

**Override por página:** En `templates/dashboard/landing.html` añadir:
```
{% block meta_description %}Win more freelance work — proposal tracking, follow-up reminders, time entries, and revenue analytics for solo consultants.{% endblock %}
```

---

### 4. CSP + arreglar security.txt

**`pyproject.toml`** — añadir `django-csp>=4.0`.

**`config/settings/base.py`** — añadir a `MIDDLEWARE` (después de SecurityMiddleware):
```python
"csp.middleware.CSPMiddleware",
```

**`config/settings/prod.py`** — añadir bloque CSP (con la sintaxis 4.x de `CONTENT_SECURITY_POLICY`):
```python
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'"],  # Tailwind utilities + form styles
        "font-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    },
}
```
(`'unsafe-inline'` en style necesario por clases inline; no se requiere en script tras retirar CDNs.)

En `dev.py` opcional: `CONTENT_SECURITY_POLICY_REPORT_ONLY` para no romper desarrollo.

**`apps/core/views_seo.py:36`** — corregir contacto:
```python
"Contact: mailto:security@dabg.dev\n"
```
(o el dominio real que use el usuario.)

---

### 5. Cache headers en static

**`config/settings/prod.py`** — añadir:
```python
WHITENOISE_MAX_AGE = 31_536_000  # 1 year (manifest hashes garantizan invalidación)
```

WhiteNoise ya emite `immutable` para archivos con hash de manifiesto, esto sólo eleva el max-age explícito.

---

## Checklist Cloudflare (fuera de código)

Estos cambios se hacen en el dashboard de Cloudflare para `dabg.dev`, no tocan el repo:

1. **Quitar inyección de `Content-Signal`** — Rules → Transform Rules → eliminar la regla que añade el header/línea, O ajustar para que no aparezca en `/robots.txt`. Si es feature global de CF (AI bot signaling), aceptar que es informativo y lighthouse lo seguirá marcando — opcional ignorarlo.
2. **Cache rule para `/static/*`** — Rules → Cache Rules → match `URI Path starts with /static/` → Cache eligibility: Eligible for cache → Edge TTL: 1 year (override origin, ya que WhiteNoise enviará el header pero CF puede cachear más).
3. **Verificar HSTS preload** — ya activo (`max-age=31536000; includeSubDomains; preload`). Submit en https://hstspreload.org si aún no.

---

## Archivos críticos a modificar

- `templates/base.html` — refactor completo del `<head>` y `<body>` wrapper.
- `templates/dashboard/landing.html` — añadir `meta_description` block.
- `apps/core/views_seo.py:36` — fix mailto.
- `config/settings/base.py` — CSP middleware en MIDDLEWARE.
- `config/settings/prod.py` — CSP policy + `WHITENOISE_MAX_AGE`.
- `pyproject.toml` — añadir `pytailwindcss`, `django-csp`.
- `deploy/Dockerfile` — añadir paso `bin/build-css.sh` antes de collectstatic.
- `tailwind.config.js` (nuevo, raíz).
- `static/css/src/app.css` (nuevo) + `static/css/src/fonts.css` (nuevo).
- `static/vendor/htmx-1.9.10.min.js` (nuevo, vendoreado).
- `static/fonts/{geist,inter,material-symbols}/*.woff2` (nuevos, subset).
- `bin/build-css.sh` (nuevo).
- **Eliminar:** `static/js/tailwind.config.js` (migrado a raíz).

---

## Verificación end-to-end

1. **Build local:**
   ```sh
   uv sync
   bin/build-css.sh
   uv run python manage.py collectstatic --noinput
   uv run python manage.py runserver
   ```
2. **Browser DevTools → Network tab** en `http://localhost:8000/`:
   - Confirmar 0 requests a `cdn.tailwindcss.com`, `unpkg.com`, `fonts.googleapis.com`, `fonts.gstatic.com`.
   - Confirmar `app.css` < 50 KiB (gzip), `htmx.min.js` ~16 KiB, fuentes < 100 KiB cada una.
3. **A11y:** Inspeccionar HTML, confirmar `<main>` envuelve contenido en landing.
4. **SEO:** `view-source:` → confirmar `<meta name="description" content="...">` presente.
5. **CSP:** `curl -sI http://localhost:8000/ | grep -i content-security-policy` → debe aparecer header.
6. **Tests:** `uv run pytest` — confirmar suite pasa (cambios no tocan lógica de negocio).
7. **Lint/types:** `uv run ruff check . && uv run mypy apps config`.
8. **Re-auditar tras deploy:**
   - Lighthouse mobile en `https://pipelancer.dabg.dev/` → LCP < 2.5s, a11y 100, SEO sin "missing meta description" ni "no main landmark".
   - `curl -sI https://pipelancer.dabg.dev/static/css/app.<hash>.css | grep -i cache-control` → `max-age=31536000, immutable`.
   - `curl -s https://pipelancer.dabg.dev/.well-known/security.txt` → contacto válido.

---

## Orden de ejecución sugerido (commits separados)

1. **commit 1 — SEO/a11y mínimo:** meta description + `<main>` wrapper + fix security.txt mailto. Rápido, bajo riesgo.
2. **commit 2 — CSP:** añadir django-csp + middleware + policy. Probar en dev como report-only primero.
3. **commit 3 — Self-host htmx + fuentes (sin tocar Tailwind):** vendoreo + cambio de URLs en base.html. Material Symbols subset incluido.
4. **commit 4 — Tailwind build:** pytailwindcss + tailwind.config.js + bin/build-css.sh + Dockerfile + retirar `<script src="cdn.tailwindcss.com">`. El más invasivo, último.
5. **commit 5 — Cache:** `WHITENOISE_MAX_AGE` + Cloudflare cache rule (manual).

Cada commit deja el sitio funcional para rollback granular.
