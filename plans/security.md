# Plan: Security Page para PropoTrack

## Contexto

Footer del landing ([templates/dashboard/landing.html:100](../templates/dashboard/landing.html#L100)) ya muestra link "Security" con `href="#"` placeholder. Privacy Policy ([templates/privacy.html](../templates/privacy.html)) y plan de Terms of Service ([plans/terms-of-service.md](./terms-of-service.md)) ya establecen el patrón legal/info: `TemplateView`, mismo skeleton de template, wiring de sitemap + footer. Este plan espeja ese patrón para una página pública que documente las prácticas de seguridad reales del proyecto, refuerce confianza, y exponga el canal de divulgación responsable que ya existe en `/.well-known/security.txt`.

Decisiones del usuario:
- **Idioma:** English (match privacy/terms)
- **Tono sobre gaps:** Middle-ground — "continuous improvements" sin listar gaps específicos (no MFA, no rate-limiting, webhook secret hardcoded permanecen sin enumerar en página pública)
- Contenido basado en auditoría del codebase actual (mayo 2026)

## Pasos de implementación

### 1. URL route

**Archivo:** `config/urls.py`

Después de línea 15 (`privacy_policy`), añadir:

```python
path("security", TemplateView.as_view(template_name="security.html"), name="security"),
```

`TemplateView` ya importado (línea 5). Sin módulo de vista nuevo.

### 2. Sitemap entry

**Archivo:** `apps/core/sitemaps.py:11`

Añadir `"security"` al `items()`:

```python
return ["accounts:login", "accounts:signup", "privacy_policy", "security"]
```

(Si plan de ToS se ejecuta antes/junto, también `"terms_of_service"`.)

### 3. Footer links

**Archivo A:** `templates/app_base.html:131-136`

Footer actual solo tiene Privacy. Añadir Security (y Terms si aplica):

```html
<div class="max-w-[1440px] mx-auto flex flex-wrap justify-between items-center gap-gutter text-center">
    <span class="font-label-sm text-label-sm text-on-surface-variant">© {% now "Y" %} PropoTrack</span>
    <div class="flex gap-6">
        <a href="{% url 'privacy_policy' %}" class="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-all">Privacy Policy</a>
        <a href="{% url 'security' %}" class="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-all">Security</a>
    </div>
</div>
```

**Archivo B:** `templates/dashboard/landing.html:100`

Reemplazar `href="#"` del link Security existente:

```html
<a href="{% url 'security' %}" class="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-all">Security</a>
```

### 4. Template

**Archivo (nuevo):** `templates/security.html`

Mismo esqueleto que `privacy.html`:
- `{% extends "base.html" %}`
- `{% block title %}Security{% endblock %}`
- `{% block meta_description %}PropoTrack Security — how we protect your data, the controls we apply, and how to report vulnerabilities.{% endblock %}`
- Container: `max-w-3xl mx-auto px-4 py-12 space-y-8`
- Header: `border-b border-outline pb-6` con `h1.font-headline-lg text-headline-lg font-display-md` y `<p class="text-body-sm text-on-background-variant mt-2">Effective: May 11, 2026</p>`
- Cada sección: `<section class="space-y-6">` con `<h2 class="font-title-lg text-title-lg">N. Title</h2>` y `<p class="text-body-md text-on-background-variant leading-relaxed">...</p>`
- Listas: `list-disc list-inside text-body-md text-on-background-variant space-y-1`
- Tabla (sección 4): mismo estilo que cookies table de privacy.html (`w-full text-body-sm ... border border-outline rounded-lg overflow-hidden`)
- Links: `text-link underline`
- Code inline: `<code>` (sin clase extra; mismo uso que privacy §4-5)

**Outline de secciones** (derivado de auditoría real del codebase):

| # | Heading | Contenido resumen |
|---|---------|-------------------|
| 1 | Introduction | Compromiso con seguridad de datos del freelancer. PropoTrack aplica defensas-en-capas a nivel app, transporte e infraestructura. Las prácticas descritas reflejan la implementación actual y evolucionan continuamente. |
| 2 | Authentication & Sessions | Email + contraseña vía `django-allauth` ([apps/accounts/models.py:10](../apps/accounts/models.py#L10)). Login únicamente por email (`ACCOUNT_LOGIN_METHODS = {"email"}`). Sesiones server-side en base de datos (no JWT, no localStorage). Cookies de sesión `HttpOnly`, `Secure`, `SameSite=Lax` en producción con timeout de 8 horas. Cambio de contraseña disponible vía `/.well-known/change-password`. |
| 3 | Password Storage | Hash con algoritmo por defecto de Django (PBKDF2-SHA256). Validadores activos: `UserAttributeSimilarityValidator`, `MinimumLengthValidator` (8 caracteres), `CommonPasswordValidator`, `NumericPasswordValidator`. Las contraseñas nunca se almacenan ni se transmiten en claro. |
| 4 | Transport Security (HTTPS/TLS) | HTTPS forzado en producción (`SECURE_SSL_REDIRECT`). HSTS activo con `max-age=31536000` (1 año), `includeSubDomains` y `preload`. Tabla con headers aplicados: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Cross-Origin-Opener-Policy`. |
| 5 | Application-Layer Defenses | CSRF tokens en todos los formularios POST (cookie `Secure`, `HttpOnly`, `SameSite=Lax`). Content Security Policy estricta: `default-src 'self'`, sin scripts inline arbitrarios, `frame-ancestors 'none'`. Plantillas Django auto-escapan output (XSS por defecto). Sin scripts de tracking o analytics de terceros cargados. |
| 6 | Per-User Data Isolation | Cada modelo de dominio hereda de `OwnedModel` con FK obligatoria al usuario propietario ([apps/core/models.py:19-33](../apps/core/models.py#L19-L33)). Aislamiento aplicado a dos niveles: (a) `QuerySet` — todas las vistas y servicios filtran por `owner=request.user` vía `OwnerQuerysetMixin` / `ProposalOwnerQuerysetMixin` ([apps/core/mixins.py](../apps/core/mixins.py)); (b) endpoints API requieren `IsAuthenticated`. Un usuario nunca puede acceder a propuestas, clientes, time entries o templates de otro usuario. |
| 7 | Data Storage | Producción: PostgreSQL 16 con credenciales desde variables de entorno, conexiones cifradas TLS. Sin almacenamiento de datos de pago — montos son valores decimales que el usuario ingresa manualmente. Sin compartir datos con terceros. Aislamiento a nivel app (sección 6) garantiza separación lógica. |
| 8 | Secrets & Configuration | Toda configuración sensible (claves, credenciales DB, secretos SMTP) se carga vía `django-environ` desde variables de entorno. `DJANGO_SECRET_KEY` requerida en producción sin valor por defecto. `DEBUG=False` en producción. Repositorio no contiene `.env` (solo `env.example`). |
| 9 | Webhook Integrity | Endpoint `/api/webhooks/proposal-events/` valida payloads con HMAC-SHA256 ([apps/exports/api_views.py:12-36](../apps/exports/api_views.py#L12-L36)). Comparación de firma con `hmac.compare_digest` (resistente a timing attacks). Sin firma válida → request rechazado. |
| 10 | Audit Trail | Modelo `ActivityLog` ([apps/core/models.py:36-70](../apps/core/models.py#L36-L70)) registra eventos de dominio (cambios de status de propuestas, follow-ups completados) vía signals. Eventos de seguridad de Django emitidos al logger `django.security` a nivel WARNING+ en producción. |
| 11 | Infrastructure | Contenedor Docker multi-stage minimalista; proceso de aplicación corre como usuario no-root (UID 1000) — superficie de escalación reducida. Health check expuesto en `/healthz`. Despliegue en Coolify con `DJANGO_SETTINGS_MODULE=config.settings.prod` forzado. Stack monitoreado y actualizado regularmente. |
| 12 | Responsible Disclosure | Si descubre una vulnerabilidad, repórtela a [security@dabg.dev](mailto:security@dabg.dev). Información del canal disponible también en formato `security.txt` estándar: [`/.well-known/security.txt`](/.well-known/security.txt). Comprometidos a responder dentro de 5 días hábiles y a no perseguir legalmente investigación de seguridad de buena fe (no scanning destructivo, no acceso a datos de otros usuarios, no DoS). Idiomas: español, inglés. |
| 13 | Continuous Improvement | Evaluamos y mejoramos continuamente nuestras prácticas de seguridad. Esta página se actualizará a medida que se incorporen nuevos controles. Las fechas efectivas indican la versión actual. |
| 14 | Contact | Reportes de vulnerabilidades: [security@dabg.dev](mailto:security@dabg.dev). Consultas generales sobre privacidad o datos: [noreply@pipelancer.dabg.dev](mailto:noreply@pipelancer.dabg.dev) (ver [Privacy Policy](/privacy)). |

**Notas de redacción:**
- Tono profesional, declarativo, sin marketing-speak ("military-grade", "bank-level" — evitar).
- Mismo nivel de detalle técnico que privacy.html §4-5 (menciona `django-allauth`, `<code>sessionid</code>`, etc.).
- Cifras concretas donde existen (HSTS 1 año, sesión 8h, validador min 8 chars).
- Sin enumerar gaps específicos; sección 13 cumple el rol de "honesty hatch" sin convertirse en checklist de debilidades.

## Archivos a crear/modificar

- **Crear:** `templates/security.html`
- **Modificar:** `config/urls.py` — añadir path
- **Modificar:** `apps/core/sitemaps.py` — añadir `"security"` al `items()`
- **Modificar:** `templates/app_base.html` — añadir link Security en footer
- **Modificar:** `templates/dashboard/landing.html:100` — wirear link existente al URL name

**Reutilización:**
- `TemplateView` (ya importado en `config/urls.py:5`) — sin vista nueva.
- Patrón de footer y estilo de template heredado 100% de `privacy.html` y plan ToS.
- `security.txt` existente ([apps/core/views_seo.py:27-41](../apps/core/views_seo.py#L27-L41)) — la página HTML referencia esta URL, no la duplica.

## Verificación

```bash
uv run python manage.py runserver
```

- [ ] `GET /security` → 200; renderiza todas las secciones sin errores de template
- [ ] `GET /sitemap.xml` incluye entrada `/security`
- [ ] Footer de `app_base.html` (vistas autenticadas) muestra link Security clickeable
- [ ] Link Security del landing footer navega a `/security` (ya no `#`)
- [ ] Link `/.well-known/security.txt` en sección 12 resuelve a `apps/core/views_seo.py:security_txt`
- [ ] `uv run ruff check . && uv run ruff format --check .` pasa
- [ ] `uv run pytest --no-cov -q` pasa (no requiere tests propios para `TemplateView`; existentes no deben romper)
- [ ] Visual: tipografía/espaciado coincide con `/privacy` (mismo `max-w-3xl`, mismas escalas de heading, misma tabla style en sección 4)
- [ ] Fecha efectiva: **May 11, 2026**
- [ ] No filtra detalles internos de implementación que sean explotables (paths internos, versiones exactas de dependencias, archivos de config); auditoría informa contenido pero texto público se mantiene a nivel de control, no de configuración línea por línea.
