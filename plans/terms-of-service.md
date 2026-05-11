# Plan: Terms of Service para PropoTrack

## Contexto

Footer del landing ([templates/dashboard/landing.html:99](../templates/dashboard/landing.html#L99)) ya muestra link "Terms of Service" con `href="#"` placeholder. Privacy Policy en producción ([templates/privacy.html](../templates/privacy.html)); falta contraparte ToS. Este plan espeja el patrón de privacy — mismo `TemplateView`, misma estructura de template, mismo wiring sitemap + footer — y define contenido legal para SaaS gratuito orientado a freelancers de LATAM.

Decisiones del usuario:
- **Idioma:** English (match privacy.html)
- **Modelo:** Free SaaS, sin clausulas de billing
- **Jurisdicción:** LATAM genérico (sin pais específico; referencia ley local del usuario)
- **Secciones extra:** DMCA, Beta no-warranty, Suspension/termination, Acceptable use

## Pasos de implementación

### 1. URL route

**Archivo:** `config/urls.py`

Después de línea 15 (`privacy_policy`), añadir:

```python
path("terms", TemplateView.as_view(template_name="terms.html"), name="terms_of_service"),
```

`TemplateView` ya importado (línea 5). No requiere módulo de vista.

### 2. Sitemap entry

**Archivo:** `apps/core/sitemaps.py:11`

Añadir `"terms_of_service"` al `items()`:

```python
return ["accounts:login", "accounts:signup", "privacy_policy", "terms_of_service"]
```

### 3. Footer links

**Archivo A:** `templates/app_base.html:131-136`

Footer actual solo tiene Privacy. Añadir Terms con misma clase. Reemplazar el `<div>` interno (línea 132) por:

```html
<div class="max-w-[1440px] mx-auto flex flex-wrap justify-between items-center gap-gutter text-center">
    <span class="font-label-sm text-label-sm text-on-surface-variant">© {% now "Y" %} PropoTrack</span>
    <div class="flex gap-6">
        <a href="{% url 'privacy_policy' %}" class="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-all">Privacy Policy</a>
        <a href="{% url 'terms_of_service' %}" class="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-all">Terms of Service</a>
    </div>
</div>
```

**Archivo B:** `templates/dashboard/landing.html:99`

Reemplazar `href="#"` del link Terms existente:

```html
<a href="{% url 'terms_of_service' %}" ...>Terms of Service</a>
```

### 4. Template

**Archivo (nuevo):** `templates/terms.html`

Mismo esqueleto que `privacy.html`:
- `{% extends "base.html" %}`
- `{% block title %}Terms of Service{% endblock %}`
- `{% block meta_description %}PropoTrack Terms of Service — rules and conditions for using the platform.{% endblock %}`
- Container: `max-w-3xl mx-auto px-4 py-12 space-y-8`
- Header: `border-b border-outline pb-6` con `h1.font-headline-lg text-headline-lg font-display-md` y `<p class="text-body-sm text-on-background-variant mt-2">Effective: May 11, 2026</p>`
- Cada sección: `<section class="space-y-6">` con `<h2 class="font-title-lg text-title-lg">N. Title</h2>` y `<p class="text-body-md text-on-background-variant leading-relaxed">...</p>`
- Listas: `list-disc list-inside text-body-md text-on-background-variant space-y-1`
- Links: `text-link underline`
- Emphasis: `<strong>`

**Outline de secciones:**

| # | Heading | Contenido resumen |
|---|---------|-------------------|
| 1 | Introduction | Alcance del acuerdo; "PropoTrack" definido; aceptación por uso; elegibilidad (18+ o capacidad legal según ley local). |
| 2 | Definitions | Service, User, Account, Content (proposals/clients/time entries/templates ingresados por el usuario). |
| 3 | Account Registration | Email + password vía django-allauth; usuario responsable de confidencialidad de credenciales; una cuenta por persona; info veraz. |
| 4 | Acceptable Use | Prohibido: scraping/abuso automatizado, reverse-engineering, reventa de acceso, contenido ilegal/infractor/malicioso, suplantación, intentar acceder a datos de otros usuarios, eludir aislamiento per-user, sobrecargar infra. |
| 5 | User Content & Ownership | Usuario retiene propiedad de propuestas, datos de clientes, templates, time entries. PropoTrack recibe solo licencia limitada para almacenar, procesar y mostrar Content para operar el Service. No training sobre datos del usuario. No compartir con terceros. |
| 6 | Intellectual Property | Nombre PropoTrack, UI, código, diseño propiedad del operador. Licencia limitada, revocable, no-exclusiva para usar el Service para gestión personal freelance. Sin derechos de marca otorgados. |
| 7 | DMCA / IP Infringement | Proceso notice-and-takedown; enviar notificaciones a `noreply@freelancer-tracker.dabg.dev` con: identificación de la obra, ubicación del material infractor, contacto, declaración de buena fe, firma. Counter-notice. Cuentas reincidentes terminadas. |
| 8 | Beta / No-Warranty Disclaimer | Service "AS IS" y "AS AVAILABLE". Sin garantía de idoneidad, exactitud, uptime, operación libre de errores, ni entrega de follow-up reminders / digest emails. Analytics son informativas, no consejo financiero. |
| 9 | Limitation of Liability | En la máxima medida permitida por ley aplicable: sin responsabilidad por daños indirectos, incidentales, consecuentes, especiales; lucro cesante; pérdida de datos; pérdida de oportunidades. Responsabilidad agregada limitada a USD $0 (servicio gratuito) o monto pagado en últimos 12 meses, lo que sea mayor. |
| 10 | Indemnification | Usuario indemniza a PropoTrack contra reclamos derivados de su Content o violación de estos Terms o ley aplicable. |
| 11 | Account Suspension & Termination | Operador puede suspender/terminar por: violación de ToS, violación de Acceptable Use, fraude, requerimiento legal, inactividad prolongada (>24 meses). Usuario puede eliminar cuenta cuando quiera vía account settings o email a soporte. Al terminar: datos eliminados según Privacy Policy §6 (30 días). |
| 12 | Service Availability & Changes | Best-effort uptime; sin SLA. Features pueden cambiar o ser removidas. Cambios materiales comunicados vía aviso in-app o email. |
| 13 | Third-Party Services | Service corre en infra de terceros (Coolify host, PostgreSQL, proveedor SMTP). Sus términos también aplican donde corresponda. Sin trackers de terceros según Privacy Policy §4. |
| 14 | Privacy | Manejo de datos regido por [Privacy Policy](/privacy). |
| 15 | Governing Law | Estos Terms se rigen por las leyes del país de residencia habitual del usuario en Latinoamérica. Disputas se resuelven en cortes competentes de esa jurisdicción, salvo que normas imperativas de protección al consumidor dispongan otra cosa. |
| 16 | Changes to Terms | Operador puede revisar; versión revisada publicada en esta página con fecha efectiva actualizada; uso continuado = aceptación. |
| 17 | Severability | Si alguna cláusula es inejecutable, el resto permanece vigente. |
| 18 | Contact | `noreply@freelancer-tracker.dabg.dev` |

## Archivos a crear/modificar

- **Crear:** `templates/terms.html`
- **Modificar:** `config/urls.py` — añadir path
- **Modificar:** `apps/core/sitemaps.py` — añadir al sitemap
- **Modificar:** `templates/app_base.html` — añadir link Terms en footer
- **Modificar:** `templates/dashboard/landing.html` — enlazar link Terms existente al URL name

## Verificación

```bash
uv run python manage.py runserver
```

- [ ] `GET /terms` → 200, renderiza las 18 secciones, sin errores de template
- [ ] `GET /sitemap.xml` incluye entrada `/terms`
- [ ] Footer de `app_base.html` (vistas autenticadas) muestra ambos links Privacy + Terms, clickeables
- [ ] Link Terms del landing footer navega a `/terms` (ya no `#`)
- [ ] `uv run ruff check .` pasa
- [ ] `uv run pytest --no-cov -q` pasa (no requiere tests de vista — `TemplateView` — pero los existentes no deben romper)
- [ ] Visual: tipografía/espaciado coincide con `/privacy` (mismo ancho, misma escala de heading)
- [ ] Fecha efectiva: **May 11, 2026**
