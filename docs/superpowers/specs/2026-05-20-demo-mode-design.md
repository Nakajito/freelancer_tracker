# Demo Mode Design

**Date:** 2026-05-20  
**Status:** Approved

## Context

The landing page has a "Ver Demo" button currently pointing to `#features` (scroll anchor). Users want a real interactive demo showing all platform features with realistic fictional data — read-only, no writes allowed. A `seed_demo` command already creates a demo user (`demo@propotrack.test` / `demo1234`) with 25 proposals, 5 clients, time entries, follow-ups, templates, and retainers.

The goal: clicking "Ver Demo" auto-logs in the demo user and shows the full dashboard in read-only mode with a visible banner prompting real signup.

## Architecture

Three new pieces + targeted template changes:

1. **Context Processor** (`apps/core/context_processors.py`) — injects `is_demo: bool` into every template context by checking `request.user.email == DEMO_USER_EMAIL`
2. **Middleware** (`apps/core/middleware.py`) — intercepts all non-safe HTTP methods (POST/PUT/PATCH/DELETE) for the demo user, adds a flash message, redirects to referer or dashboard
3. **Auto-login View** (`apps/dashboard/views.py`) — `DemoAutoLoginView` at `/demo/` — logs in as demo user, redirects to dashboard. If demo user doesn't exist, redirects to landing with error message.

Settings add:
- `DEMO_USER_EMAIL = "demo@propotrack.test"` in `config/settings/base.py`
- Context processor registered in `TEMPLATES[0]['OPTIONS']['context_processors']`
- Middleware added to `MIDDLEWARE` list after `AuthenticationMiddleware`

## Components

### DemoContextProcessor
```python
# apps/core/context_processors.py
def demo_mode(request):
    is_demo = (
        hasattr(request, "user")
        and request.user.is_authenticated
        and request.user.email == settings.DEMO_USER_EMAIL
    )
    return {"is_demo": is_demo}
```

### DemoReadOnlyMiddleware
```python
# apps/core/middleware.py
SAFE_METHODS = frozenset(["GET", "HEAD", "OPTIONS"])

class DemoReadOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method not in SAFE_METHODS
            and getattr(request, "user", None)
            and request.user.is_authenticated
            and request.user.email == settings.DEMO_USER_EMAIL
        ):
            messages.info(request, _("This feature is disabled in demo mode. Create an account to use it."))
            referer = request.META.get("HTTP_REFERER", "")
            return redirect(referer or reverse("dashboard"))
        return self.get_response(request)
```

### DemoAutoLoginView
```python
# apps/dashboard/views.py
class DemoAutoLoginView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        User = get_user_model()
        try:
            user = User.objects.get(email=settings.DEMO_USER_EMAIL)
        except User.DoesNotExist:
            messages.error(request, _("Demo not available. Please sign up."))
            return redirect("landing")
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("dashboard")
```

URL: added to `apps/dashboard/urls.py` as `path("demo/", DemoAutoLoginView.as_view(), name="demo-login")`

## UI Changes

### Demo Banner (app_base.html)
Inside `<main>`, at the top of the max-width container, before `_messages.html`:

```html
{% if is_demo %}
<div class="mb-6 bg-tertiary-container text-on-tertiary-container px-4 py-3 rounded-lg flex flex-wrap items-center justify-between gap-3">
    <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-[20px]">visibility</span>
        <span class="font-label-md text-label-md">{% trans "Demo Mode" %} — {% trans "You're viewing sample data. All edits are disabled." %}</span>
    </div>
    <a href="{% url 'account_signup' %}" class="font-label-md text-label-md font-semibold underline hover:no-underline">{% trans "Create your free account →" %}</a>
</div>
{% endif %}
```

### New Proposal Button (app_base.html sidebar)
Replace the `<a href="proposal-create">` with conditional:
```html
{% if is_demo %}
<span class="w-full bg-surface-container-high text-on-surface-variant ... opacity-60 cursor-not-allowed"
      title="{% trans 'Disabled in demo mode' %}">
    <span class="material-symbols-outlined text-[20px]">add</span>
    {% trans "New Proposal" %}
</span>
{% else %}
<a href="{% url 'proposal-create' %}" ...>{% trans "New Proposal" %}</a>
{% endif %}
```

### Action Buttons in Templates
All Create/Edit/Delete buttons across templates get wrapped with `{% if not is_demo %}...{% endif %}` or replaced with a disabled variant with tooltip. Affected templates:
- `proposals/proposal_list.html` — Create + Delete buttons
- `proposals/proposal_detail.html` — Edit + Delete buttons  
- `proposals/client_list.html` — Create + Delete buttons
- `followups/followup_list.html` — Create + Complete + Delete buttons
- `timetracking/timeentry_list.html` — Create + Delete buttons
- `timetracking/retainer_list.html` — Create button
- `templates_app/template_list.html` — Create + Delete buttons
- `templates_app/template_detail.html` — Edit + Delete buttons

Pattern per button (native `title` tooltip, no Bootstrap dependency):
```html
{% if is_demo %}
<span class="... opacity-50 cursor-not-allowed" title="{% trans 'Disabled in demo mode' %}">{{ label }}</span>
{% else %}
<a href="...">{{ label }}</a>
{% endif %}
```

### Landing Page
Change line 70 `href="#features"` to `href="{% url 'demo-login' %}"`.

## Data Flow

```
User clicks "Ver Demo"
  → GET /demo/
  → DemoAutoLoginView: login(demo_user)
  → redirect /dashboard/
  → DashboardView: renders with demo user's data
  → DemoContextProcessor: is_demo=True in context
  → Banner shown, write buttons disabled

User tries POST (e.g., create proposal)
  → DemoReadOnlyMiddleware intercepts
  → Flash message: "Disabled in demo mode"
  → Redirect to referer
```

## Affected Files

| File | Change |
|------|--------|
| `config/settings/base.py` | Add `DEMO_USER_EMAIL`, register context processor + middleware |
| `apps/core/context_processors.py` | NEW — `demo_mode` processor |
| `apps/core/middleware.py` | NEW — `DemoReadOnlyMiddleware` |
| `apps/dashboard/views.py` | Add `DemoAutoLoginView` |
| `apps/dashboard/urls.py` | Add `demo/` URL |
| `templates/dashboard/landing.html` | Change "Ver Demo" href |
| `templates/app_base.html` | Banner + disabled New Proposal button |
| 8 feature templates | Disable CRUD action buttons |

## Testing

1. Run `uv run python manage.py seed_demo` to ensure demo user exists
2. Click "Ver Demo" on landing → should land on dashboard as demo user
3. Verify banner appears with "Create your free account" CTA
4. Try clicking New Proposal in sidebar → should show tooltip, not navigate
5. Navigate to `/proposals/create/` directly → should redirect with flash message
6. Try submitting any form (POST) → middleware blocks, shows message
7. All read views (list, detail, analytics) should work normally
8. Logout → returns to normal state

### Automated tests
- `test_demo_auto_login_view` — GET redirects to dashboard as demo user
- `test_demo_auto_login_no_user` — redirects to landing if demo user missing
- `test_demo_middleware_blocks_post` — POST as demo user → redirect + message
- `test_demo_middleware_passes_get` — GET as demo user → passes through
- `test_demo_middleware_passes_normal_user_post` — non-demo user POST → passes
- `test_is_demo_context` — `is_demo=True` in context for demo user
