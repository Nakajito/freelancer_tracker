# Fix prod filtros + mezcla idioma

## Context

Proyecto Django 6.0.5 (Pipelancer) desplegado en Coolify. Dos bugs reportados solo en producción:

1. **Filtros no aplican nada** en `/proposals/` — usuario cambia `<select>` y queryset no cambia.
2. **Mezcla es/en** en misma página — algunos strings traducidos, otros en inglés default.

Ambos bugs causados por divergencia dev/prod (CSP + Docker build), no por código defectuoso en sí.

---

## Root cause #1 — Filtros no aplican

**File:** [templates/proposals/proposal_list.html:33-72](templates/proposals/proposal_list.html#L33-L72)

Cada `<select>` del form depende de handler inline:
```html
<select name="status" onchange="document.getElementById('filter-form').submit()">
```

**File:** [config/settings/prod.py:54-77](config/settings/prod.py#L54-L77)

CSP prod:
```python
"script-src": ["'self'", "https://js.stripe.com"],
```

**No incluye `'unsafe-inline'`** → navegador bloquea atributos `onchange="..."` en producción. Form nunca se envía al cambiar select → filtro no aplica. En dev (sin CSP estricta) funciona.

Confirmación: DevTools Console en prod muestra `Refused to execute inline event handler because it violates the following Content Security Policy directive: "script-src 'self' https://js.stripe.com"`.

---

## Root cause #2 — Mezcla es/en

**File:** [deploy/Dockerfile:25-32](deploy/Dockerfile#L25-L32)

Build no copia `locale/`:
```dockerfile
COPY apps/ ./apps/
COPY config/ ./config/
COPY templates/ ./templates/
COPY static/ ./static/
# falta: COPY locale/ ./locale/
```

**File:** [deploy/entrypoint.sh](deploy/entrypoint.sh)

Tampoco corre `compilemessages`. Resultado: contenedor sin `.mo` español. Django cae a msgid (inglés) para todo `{% trans %}`. Mezcla con strings hardcoded en español/inglés → visible en UI.

`LANGUAGE_CODE = "en"`, `LANGUAGES = [("en", ...), ("es", ...)]`, `LOCALE_PATHS = [BASE_DIR / "locale"]` correcto en `base.py`. `LocaleMiddleware` posición correcta. `i18n_patterns()` envuelve URLs. Único faltante: `.mo` en contenedor.

---

## Fix plan

### Fix A — Filtros (eliminar inline handler)

**File:** [templates/proposals/proposal_list.html](templates/proposals/proposal_list.html)

Quitar los 5 `onchange="..."` de selects (líneas 33, 42, 51, 60, 69). Reemplazar con script externo.

1. Crear `static/js/filter-autosubmit.js`:
   ```js
   document.addEventListener('DOMContentLoaded', () => {
     const form = document.getElementById('filter-form');
     if (!form) return;
     form.querySelectorAll('select').forEach(s => {
       s.addEventListener('change', () => form.submit());
     });
   });
   ```

2. En template:
   ```html
   <script src="{% static 'js/filter-autosubmit.js' %}" defer></script>
   ```

3. Borrar `onchange` de los 5 selects.

Auditar resto:
```bash
grep -rn --include='*.html' -E 'on(change|click|submit|input|load)=' templates/
```
Migrar cualquier otro inline handler — pueden estar bloqueados pero no reportados.

### Fix B — i18n (compilar y copiar .mo)

**File:** [deploy/Dockerfile](deploy/Dockerfile)

1. Agregar `gettext` al `apt-get install` (línea ~13):
   ```dockerfile
   RUN apt-get update && apt-get install -y --no-install-recommends \
       libpq5 \
       curl \
       gettext \
       && rm -rf /var/lib/apt/lists/* \
       ...
   ```

2. Agregar después de `COPY static/ ./static/` (línea 28):
   ```dockerfile
   COPY locale/ ./locale/
   ```

3. Agregar después de `bin/build-css.sh` en el `RUN` final:
   ```dockerfile
   && .venv/bin/python manage.py compilemessages --ignore=.venv
   ```

Compilar en build (no entrypoint) evita race condition y centraliza dependencia `gettext`.

### Fix C — Limpieza sintaxis except (opcional)

**File:** [apps/proposals/views.py:48,53](apps/proposals/views.py#L48-L53)

`except ValueError, TypeError:` parsea como tupla en Python 3.14 (funciona), pero ambiguo. Cambiar a:
```python
except (ValueError, TypeError):
```

No causa bug reportado. Solo legibilidad.

---

## Critical files

| File | Cambio |
|------|--------|
| `templates/proposals/proposal_list.html` | Quitar 5x `onchange` inline, agregar `<script src>` |
| `static/js/filter-autosubmit.js` | **NUEVO** — handler externo |
| `deploy/Dockerfile` | Instalar `gettext`, `COPY locale/`, `compilemessages` |
| `apps/proposals/views.py` | (opcional) fix sintaxis except |

---

## Verification

1. **Local repro filtro** con CSP prod activo:
   ```bash
   DJANGO_SETTINGS_MODULE=config.settings.prod \
     DJANGO_SECRET_KEY=test ALLOWED_HOSTS=localhost \
     SECURE_SSL_REDIRECT=False \
     uv run python manage.py runserver
   ```
   Abrir `/proposals/`, cambiar `<select>` status → debe recargar con `?status=...`.

2. **Local repro i18n** con docker:
   ```bash
   docker compose -f deploy/docker-compose.yml up --build
   docker exec -it <id> ls /app/locale/es/LC_MESSAGES/
   ```
   Debe mostrar `django.mo`. Setear `language_preference=es`, recargar → todo español.

3. **Tests**:
   ```bash
   uv run pytest tests/test_proposals.py -k filter
   uv run pytest --cov --cov-fail-under=75
   ```
   Agregar regression guard: test que verifique HTML del filter form NO contiene `onchange=`.

4. **Deploy Coolify**: re-deploy. DevTools Console → ya no error CSP inline handler. Filtros submit al cambiar. Página español sin mezcla.

5. **Sanity post-deploy**:
   ```bash
   curl -I https://<prod-url>/static/js/filter-autosubmit.js  # 200
   ```
