# Plan: Privacy Policy Específica del Proyecto

## Objetivo

Crear página "Privacy Policy" específica para PropoTrack que Dokumenta qué datos se recopilan, cómo se usan, cookies, y derechos de usuarios.

## Pasos de implementación

### 1. Crear vista de Privacy Policy

**Archivo:** `apps/core/views_privacy.py`

```python
from django.shortcuts import render
from django.views.decorators.cache import cache_page

@cache_page(60 * 60 * 24)  # 24 horas
def privacy_policy(request):
    return render(request, "privacy.html")
```

### 2. Crear template

**Archivo:** `templates/privacy.html`

Extiende `base.html` con contenido específico:

| Sección | Contenido |
|---------|-----------|
| **Introducción** | "PropoTrack Privacy Policy", fecha efectiva |
| **Datos que recopilamos** | User (email, name), Proposal (title, platform, amount, status, job_url, proposal_url, sent_date, response dates), Client (name), FollowUp (description, due_date, completed_at), TimeEntry (hours, description, date), ProposalTemplate (name, body), ActivityLog |
| **Cómo usamos los datos** | Gestionar propuestas, seguir-up, tracking de tiempo, analytics, notificaciones |
| **Cookies** | sessionid (Django), csrftoken, Htmx-Request header |
| **Almacenamiento** | DB (SQLite dev / Postgres prod), django-allauth |
| **Derechos GDPR/CCPA** | Acceso, rectificación, supresión, portabilidad |
| **Contacto** | Email de contacto desde settings o fijo |

### 3. Añadir URL a config/urls.py

```python
from apps.core.views_privacy import privacy_policy

urlpatterns = [
    # ... existing lines
    path("privacy", privacy_policy, name="privacy_policy"),
]
```

### 4. Añadir al sitemap (apps/core/sitemaps.py)

```python
class StaticViewSitemap(Sitemap):
    def items(self):
        return [
            # ... existing
            ("privacy_policy", {"priority": 0.3}),
        ]
```

### 5. Añadir link en footer (templates/base.html o app_base.html)

```html
<a href="{% url 'privacy_policy' %}">Privacy</a>
```

## Archivos a crear/modificar

- **Crear:** `apps/core/views_privacy.py`
- **Crear:** `templates/privacy.html`
- **Modificar:** `config/urls.py` — añadir path
- **Modificar:** `apps/core/sitemaps.py` — añadir al sitemap
- **Modificar:** `templates/base.html` o `templates/app_base.html` — añadir link en footer

## Verificación

- [ ] GET /privacy retorna 200
- [ ] Template renderiza sin errores
- [ ] Link visible en footer de páginas autenticadas
- [ ] Incluida en sitemap.xml