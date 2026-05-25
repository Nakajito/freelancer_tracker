# Cloudflare Turnstile CAPTCHA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Cloudflare Turnstile (managed mode) to the login and signup forms to block bots, with server-side token verification and zero new Python dependencies.

**Architecture:** A `TurnstileFormMixin` extends allauth's `LoginForm` and `SignupForm` via `ACCOUNT_FORMS` setting — its `clean()` verifies the `cf-turnstile-response` POST token against Cloudflare's siteverify API. The widget is rendered via a `<div class="cf-turnstile">` in each template. Validation is skipped when `TURNSTILE_ENABLED=False` (dev/test default). Remote IP is included when available (`LoginForm` stores `self.request`; `SignupForm` does not — remoteip is optional in CF's API).

**Tech Stack:** Python stdlib `urllib` (no new deps), django-allauth 65.x, Tailwind CSS templates, django-csp.

---

## Important: allauth 65.x API Notes

- `LoginForm.__init__` (line 74 of allauth source) pops `request` from kwargs: `self.request = kwargs.pop("request", None)`. **`self.request` IS available** in `TurnstileLoginForm.clean()`.
- `SignupView` does NOT pass `request` to `SignupForm` kwargs. **`self.request` is NOT available** in `TurnstileSignupForm.clean()`. Use `getattr(self, 'request', None)` safely — `remoteip` is optional in CF's API.
- allauth reads `ACCOUNT_FORMS` via `get_form_class(app_settings.FORMS, "login"/"signup", ...)` — setting `ACCOUNT_FORMS` in `base.py` is the correct hook.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `apps/accounts/turnstile.py` | `validate_turnstile()` — pure validation logic |
| Create | `tests/test_turnstile.py` | Unit tests for `validate_turnstile()` |
| Modify | `apps/accounts/forms.py` | Add `TurnstileFormMixin`, `TurnstileLoginForm`, `TurnstileSignupForm` |
| Modify | `apps/accounts/context_processors.py` | Add `turnstile()` context processor to expose `TURNSTILE_SITE_KEY` |
| Modify | `config/settings/base.py` | Add `TURNSTILE_*` settings, `ACCOUNT_FORMS`, register context processor |
| Modify | `config/settings/prod.py` | Update CSP: `script-src`, `frame-src`, `connect-src` |
| Modify | `templates/account/login.html` | Add widget `<div class="cf-turnstile">` |
| Modify | `templates/account/signup.html` | Add widget `<div class="cf-turnstile">` |
| Modify | `templates/auth_base.html` | Add Turnstile `<script>` tag via `{% block extra_js %}` |

---

## Task 1: `validate_turnstile()` — TDD

**Files:**
- Create: `apps/accounts/turnstile.py`
- Create: `tests/test_turnstile.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_turnstile.py`:

```python
import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.accounts.turnstile import validate_turnstile

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


@override_settings(TURNSTILE_ENABLED=False)
def test_disabled_skips_validation():
    # Must not raise even with empty token
    validate_turnstile("", "")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_empty_token_raises():
    with pytest.raises(ValidationError, match="complete the security check"):
        validate_turnstile("", "1.2.3.4")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_valid_token_passes():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"success": True}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        validate_turnstile("valid-token", "1.2.3.4")  # must not raise


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_invalid_token_raises():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"success": False}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(ValidationError, match="Security check failed"):
            validate_turnstile("bad-token", "1.2.3.4")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_network_error_fails_open():
    with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
        # Must not raise — fail open
        validate_turnstile("any-token", "1.2.3.4")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_no_remote_ip_omits_remoteip_field():
    """remoteip is optional — must work when empty."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"success": True}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        validate_turnstile("token", "")
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        import urllib.parse
        body = urllib.parse.parse_qs(req.data.decode())
        assert "remoteip" not in body
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_turnstile.py --no-cov -v
```

Expected: `ImportError` — `apps.accounts.turnstile` doesn't exist yet.

- [ ] **Step 3: Implement `apps/accounts/turnstile.py`**

Create `apps/accounts/turnstile.py`:

```python
import json
import logging
import urllib.parse
import urllib.request
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def validate_turnstile(token: str, remote_ip: str = "") -> None:
    if not getattr(settings, "TURNSTILE_ENABLED", False):
        return

    if not token:
        raise ValidationError(_("Please complete the security check."))

    payload: dict[str, str] = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(SITEVERIFY_URL, data=data)
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
    except Exception:
        logger.warning(
            "Turnstile siteverify request failed — failing open", exc_info=True
        )
        return

    if not result.get("success"):
        raise ValidationError(_("Security check failed. Please try again."))
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_turnstile.py --no-cov -v
```

Expected:
```
tests/test_turnstile.py::test_disabled_skips_validation PASSED
tests/test_turnstile.py::test_empty_token_raises PASSED
tests/test_turnstile.py::test_valid_token_passes PASSED
tests/test_turnstile.py::test_invalid_token_raises PASSED
tests/test_turnstile.py::test_network_error_fails_open PASSED
tests/test_turnstile.py::test_no_remote_ip_omits_remoteip_field PASSED
6 passed
```

- [ ] **Step 5: Run full suite**

```bash
uv run pytest --no-cov -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/turnstile.py tests/test_turnstile.py
git commit -m "feat: add validate_turnstile() for Cloudflare Turnstile verification"
```

---

## Task 2: Form overrides — TDD

**Files:**
- Modify: `apps/accounts/forms.py`
- Create: `tests/test_turnstile_forms.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_turnstile_forms.py`:

```python
"""
Tests for TurnstileFormMixin using a stub parent form.

We test the mixin in isolation — not through LoginForm/SignupForm — because
allauth's LoginForm.clean() hits the DB to authenticate, which would mask
whether validate_turnstile() is called at all.
"""
from unittest.mock import patch

import pytest
from django import forms as dj_forms
from django.test import RequestFactory, override_settings

from apps.accounts.forms import TurnstileFormMixin


class _StubForm(dj_forms.Form):
    """Minimal form whose clean() returns {} without side effects."""
    def clean(self):
        return {}


class _MixinForm(TurnstileFormMixin, _StubForm):
    """Concrete form using the mixin with a neutral parent."""
    pass


@pytest.fixture
def factory():
    return RequestFactory()


@override_settings(TURNSTILE_ENABLED=False)
def test_mixin_disabled_skips_validate(factory):
    """TURNSTILE_ENABLED=False → validate_turnstile is still called but no-ops."""
    request = factory.post("/", {"cf-turnstile-response": ""})
    form = _MixinForm(data=request.POST)
    form.request = request  # simulate LoginForm behaviour

    with patch("apps.accounts.forms.validate_turnstile") as mock_vt:
        mock_vt.return_value = None
        form.clean()

    mock_vt.assert_called_once_with("", request.META["REMOTE_ADDR"])


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_mixin_passes_token_and_ip(factory):
    """Token and REMOTE_ADDR are forwarded to validate_turnstile."""
    request = factory.post("/", {"cf-turnstile-response": "tok"}, REMOTE_ADDR="5.5.5.5")
    form = _MixinForm(data=request.POST)
    form.request = request

    with patch("apps.accounts.forms.validate_turnstile") as mock_vt:
        mock_vt.return_value = None
        form.clean()

    mock_vt.assert_called_once_with("tok", "5.5.5.5")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_mixin_no_request_passes_empty_ip():
    """When self.request is absent (SignupForm case), remote_ip is ''."""
    form = _MixinForm(data={"cf-turnstile-response": "tok"})
    # No form.request set — mimics SignupForm which doesn't receive request kwarg

    with patch("apps.accounts.forms.validate_turnstile") as mock_vt:
        mock_vt.return_value = None
        form.clean()

    mock_vt.assert_called_once_with("tok", "")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_mixin_missing_token_calls_validate_with_empty(factory):
    """Missing cf-turnstile-response → validate called with '' (it raises ValidationError)."""
    from django.core.exceptions import ValidationError

    request = factory.post("/", {})  # no cf-turnstile-response key
    form = _MixinForm(data=request.POST)
    form.request = request

    with patch("apps.accounts.forms.validate_turnstile", side_effect=ValidationError("check")):
        with pytest.raises(ValidationError):
            form.clean()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_turnstile_forms.py --no-cov -v
```

Expected: `ImportError` — `TurnstileLoginForm`/`TurnstileSignupForm` don't exist yet.

- [ ] **Step 3: Add form classes to `apps/accounts/forms.py`**

Add to the **end** of the existing `apps/accounts/forms.py` (after `DeactivateAccountForm`):

```python
from allauth.account.forms import LoginForm, SignupForm

from apps.accounts.turnstile import validate_turnstile


class TurnstileFormMixin:
    def clean(self):
        cleaned_data = super().clean()
        token = self.data.get("cf-turnstile-response", "")
        request = getattr(self, "request", None)
        remote_ip = request.META.get("REMOTE_ADDR", "") if request else ""
        validate_turnstile(token, remote_ip)
        return cleaned_data


class TurnstileLoginForm(TurnstileFormMixin, LoginForm):
    pass


class TurnstileSignupForm(TurnstileFormMixin, SignupForm):
    pass
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_turnstile_forms.py --no-cov -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest --no-cov -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/forms.py tests/test_turnstile_forms.py
git commit -m "feat: add TurnstileLoginForm and TurnstileSignupForm"
```

---

## Task 3: Settings wiring

**Files:**
- Modify: `config/settings/base.py`
- Modify: `config/settings/prod.py`
- Modify: `apps/accounts/context_processors.py`

No tests needed — settings changes are covered by the existing suite plus integration through the form tests.

- [ ] **Step 1: Add Turnstile settings to `config/settings/base.py`**

Find the `ACCOUNT_LOGIN_METHODS` block (around line 90+). Add below it:

```python
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
TURNSTILE_ENABLED = env.bool("TURNSTILE_ENABLED", default=False)

ACCOUNT_FORMS = {
    "login": "apps.accounts.forms.TurnstileLoginForm",
    "signup": "apps.accounts.forms.TurnstileSignupForm",
}
```

- [ ] **Step 2: Register `turnstile` context processor in `config/settings/base.py`**

Find the `context_processors` list in `TEMPLATES`. Add after `"apps.core.context_processors.demo_mode"`:

```python
"apps.accounts.context_processors.turnstile",
```

- [ ] **Step 3: Add `turnstile()` function to `apps/accounts/context_processors.py`**

Add to the end of the existing file:

```python
def turnstile(request):
    from django.conf import settings
    return {
        "TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", ""),
    }
```

- [ ] **Step 4: Update CSP in `config/settings/prod.py`**

Find the `CONTENT_SECURITY_POLICY` dict. Update three directives:

```python
# Before:
"script-src": ["'self'"],
"connect-src": ["'self'"],
"frame-src": ["'none'"],

# After:
"script-src": ["'self'", "https://challenges.cloudflare.com"],
"connect-src": ["'self'", "https://challenges.cloudflare.com"],
"frame-src": ["https://challenges.cloudflare.com"],
```

Note: `'none'` and a domain cannot coexist in `frame-src` — replace `["'none'"]` entirely with `["https://challenges.cloudflare.com"]`. The `frame-ancestors: 'none'` directive (which prevents others from embedding Pipelancer) is separate and unchanged.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest --no-cov -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add config/settings/base.py config/settings/prod.py apps/accounts/context_processors.py
git commit -m "feat: wire Turnstile settings, ACCOUNT_FORMS, context processor, and CSP"
```

---

## Task 4: Templates — widget and script

**Files:**
- Modify: `templates/account/login.html`
- Modify: `templates/account/signup.html`
- Modify: `templates/auth_base.html`

No automated tests — verify visually with dev server using `TURNSTILE_SITE_KEY=1x00000000000000000000AA` (Cloudflare's always-passes test key).

- [ ] **Step 1: Add widget to `templates/account/login.html`**

Find the submit button block:
```html
    <button class="w-full py-3 px-4 rounded-lg bg-primary
```

Add the widget immediately **before** that button:

```html
    {% if TURNSTILE_SITE_KEY %}
    <div class="cf-turnstile" data-sitekey="{{ TURNSTILE_SITE_KEY }}" data-theme="auto"></div>
    {% endif %}

    <button class="w-full py-3 px-4 rounded-lg bg-primary
```

- [ ] **Step 2: Add widget to `templates/account/signup.html`**

Find the submit button:
```html
    <button class="w-full mt-2 bg-primary
```

Add widget immediately **before** it:

```html
    {% if TURNSTILE_SITE_KEY %}
    <div class="cf-turnstile" data-sitekey="{{ TURNSTILE_SITE_KEY }}" data-theme="auto"></div>
    {% endif %}

    <button class="w-full mt-2 bg-primary
```

- [ ] **Step 3: Add script to `templates/auth_base.html`**

Find the closing `{% endblock %}` of the file (line 71: `{% block content %}{% endblock %}`). `auth_base.html` extends `base.html` which has `{% block extra_js %}{% endblock %}` at line 33.

Add a new block before the final `{% block content %}{% endblock %}`:

```html
{% block extra_js %}
{% if TURNSTILE_SITE_KEY %}
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Verify with test site key**

Start the dev server with a test site key (Cloudflare's always-passes test key renders the widget without real CF validation):

```bash
TURNSTILE_SITE_KEY=1x00000000000000000000AA uv run python manage.py runserver
```

Open `http://localhost:8000/accounts/login/` and `http://localhost:8000/accounts/signup/`. You should see the Turnstile widget checkbox rendered before the submit button on both pages.

- [ ] **Step 5: Commit**

```bash
git add templates/account/login.html templates/account/signup.html templates/auth_base.html
git commit -m "feat: add Cloudflare Turnstile widget to login and signup templates"
```

---

## Deploy Checklist

Add these env vars in Coolify before deploying:

```
TURNSTILE_SITE_KEY=<from Cloudflare dashboard>
TURNSTILE_SECRET_KEY=<from Cloudflare dashboard>
TURNSTILE_ENABLED=True
```

Cloudflare Turnstile test keys (for staging):
- Site key (always passes): `1x00000000000000000000AA`
- Secret key (always passes): `1x0000000000000000000000000000000AA`
