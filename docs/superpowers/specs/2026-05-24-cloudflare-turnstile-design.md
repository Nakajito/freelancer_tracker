# Cloudflare Turnstile CAPTCHA — Login & Signup

**Date:** 2026-05-24  
**Status:** Approved  
**Scope:** Add Cloudflare Turnstile (managed mode) to login and signup forms to block bots

---

## Context

Auth uses django-allauth with custom templates (`templates/account/login.html`, `templates/account/signup.html`). Forms are plain Django POST. CSP in prod is strict (`script-src: 'self'`). Turnstile requires `https://challenges.cloudflare.com` added to CSP.

Turnstile keys already created in Cloudflare dashboard. Keys stored as env vars.

---

## Architecture

```
POST /accounts/login/ or /accounts/signup/
        │
        ▼
  allauth view
        │
        ▼
  TurnstileLoginForm / TurnstileSignupForm
  (extends allauth LoginForm / SignupForm via ACCOUNT_FORMS setting)
        │
        ▼  clean()
  validate_turnstile(token, remote_ip)
        │
        ├── TURNSTILE_ENABLED=False → skip (dev / test)
        │
        └── TURNSTILE_ENABLED=True → POST challenges.cloudflare.com/turnstile/v0/siteverify
                │
                ├── success=True  → form valid, continues normally
                ├── success=False → ValidationError → existing error block in template
                └── timeout/error → log warning, fail open (don't block legitimate users)
```

---

## Environment Variables

```
TURNSTILE_SITE_KEY=0x...       # public — rendered in template
TURNSTILE_SECRET_KEY=0x...     # private — backend only, never in template
TURNSTILE_ENABLED=True         # False in dev and test
```

---

## Components

### 1. `apps/accounts/turnstile.py` — validation logic

Pure function, no Django dependencies except `settings` and `ValidationError`.

```python
import logging
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def validate_turnstile(token: str, remote_ip: str) -> None:
    """Verify a Turnstile token against Cloudflare's siteverify API.

    Raises ValidationError on failure. Fails open on network errors
    to avoid blocking legitimate users during Cloudflare downtime.
    """
    if not getattr(settings, "TURNSTILE_ENABLED", False):
        return

    if not token:
        raise ValidationError(_("Please complete the security check."))

    try:
        response = requests.post(
            SITEVERIFY_URL,
            data={
                "secret": settings.TURNSTILE_SECRET_KEY,
                "response": token,
                "remoteip": remote_ip,
            },
            timeout=5,
        )
        data = response.json()
    except Exception:
        logger.warning("Turnstile siteverify request failed — failing open", exc_info=True)
        return

    if not data.get("success"):
        raise ValidationError(_("Security check failed. Please try again."))
```

### 2. `apps/accounts/forms.py` — form overrides

Add to existing `forms.py` (alongside `ProfileForm`, etc.):

```python
from allauth.account.forms import LoginForm, SignupForm
from apps.accounts.turnstile import validate_turnstile


class TurnstileFormMixin:
    def clean(self):
        cleaned_data = super().clean()
        token = self.data.get("cf-turnstile-response", "")
        remote_ip = getattr(self, "_remote_ip", "")
        validate_turnstile(token, remote_ip)
        return cleaned_data


class TurnstileLoginForm(TurnstileFormMixin, LoginForm):
    pass


class TurnstileSignupForm(TurnstileFormMixin, SignupForm):
    pass
```

`_remote_ip` is set by the allauth view via `form.request` — injected in the view layer. See data flow below.

**Remote IP injection:** allauth passes `request` to the form. Override `__init__` to capture it:

```python
class TurnstileFormMixin:
    def __init__(self, *args, **kwargs):
        self.request = kwargs.get("request")  # allauth passes request kwarg
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        token = self.data.get("cf-turnstile-response", "")
        remote_ip = self.request.META.get("REMOTE_ADDR", "") if self.request else ""
        validate_turnstile(token, remote_ip)
        return cleaned_data
```

### 3. `config/settings/base.py` — new settings

```python
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
TURNSTILE_ENABLED = env.bool("TURNSTILE_ENABLED", default=False)

ACCOUNT_FORMS = {
    "login": "apps.accounts.forms.TurnstileLoginForm",
    "signup": "apps.accounts.forms.TurnstileSignupForm",
}
```

### 4. `config/settings/prod.py` — CSP updates

Add to existing `CONTENT_SECURITY_POLICY` directives:

```python
"script-src": ["'self'", "https://challenges.cloudflare.com"],
"frame-src": ["https://challenges.cloudflare.com"],   # widget iframe
"connect-src": ["'self'", "https://challenges.cloudflare.com"],
```

### 5. `apps/accounts/context_processors.py` — expose site key

Add to existing `preferences` context processor (or create a separate one):

```python
def turnstile(request):
    from django.conf import settings
    return {
        "TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", ""),
    }
```

Register in `base.py` `TEMPLATES[0]["OPTIONS"]["context_processors"]`.

### 6. Templates — widget

**`templates/account/login.html`** — add before the submit button:

```html
{% if TURNSTILE_SITE_KEY %}
<div class="cf-turnstile" data-sitekey="{{ TURNSTILE_SITE_KEY }}" data-theme="auto"></div>
{% endif %}
```

**`templates/account/signup.html`** — same, before submit button.

**`templates/auth_base.html`** — add Turnstile script (loaded only when site key present):

```html
{% if TURNSTILE_SITE_KEY %}
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
{% endif %}
```

---

## Data Flow — Token Lifecycle

```
1. Browser loads page → CF JS renders widget, runs challenge silently
2. User completes form → cf-turnstile-response token included in POST body
3. TurnstileFormMixin.clean() extracts token from self.data
4. validate_turnstile() POSTs to CF siteverify with token + secret + IP
5. CF verifies token (one-time use, tied to domain, expires ~5min)
6. success=true → clean() returns normally
7. success=false → ValidationError shown in existing error <div>
8. Network error → warning logged, request proceeds (fail open)
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Token missing (bot skipped JS) | `ValidationError("Please complete the security check.")` |
| Token invalid / expired | `ValidationError("Security check failed. Please try again.")` |
| CF siteverify timeout (>5s) | Log warning, fail open — user proceeds |
| `TURNSTILE_ENABLED=False` | Skip all validation (dev, test) |

---

## Testing

**`tests/test_turnstile.py`** — unit tests, no DB needed:

- `validate_turnstile()` with `TURNSTILE_ENABLED=False` → no-op
- `validate_turnstile()` with empty token → `ValidationError`
- `validate_turnstile()` with valid token (mock `requests.post` → `{"success": true}`) → no exception
- `validate_turnstile()` with invalid token (mock → `{"success": false}`) → `ValidationError`
- `validate_turnstile()` with network error (mock raises `requests.Timeout`) → no exception (fail open)

**Existing test suite:** `TURNSTILE_ENABLED` defaults to `False` in base settings — no existing tests break.

---

## What Does NOT Change

- allauth login/signup flow, session handling, redirects
- CSRF handling
- Existing CSP in dev (Turnstile widget hidden when `TURNSTILE_SITE_KEY` is empty)
- Password reset, email confirmation flows (Turnstile not added there)

---

## Env Var Checklist for Deploy

Add to Coolify environment:
```
TURNSTILE_SITE_KEY=<from CF dashboard>
TURNSTILE_SECRET_KEY=<from CF dashboard>
TURNSTILE_ENABLED=True
```
