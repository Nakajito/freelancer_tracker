# Cloudflare DNS + Proxy Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Django app work correctly behind Cloudflare's proxy: real user IPs in logs, static asset caching at CF edge, and all security/CSRF features intact.

**Architecture:** Add `CloudflareIPMiddleware` as the first middleware in the stack — it reads `CF-Connecting-IP` (the header Cloudflare always sets to the real visitor IP) and overwrites `REMOTE_ADDR` so downstream code sees the correct IP. Settings gain `USE_X_FORWARDED_HOST = True` so `request.get_host()` reflects the real domain. Cloudflare dashboard config handles edge caching for `/static/*`.

**Tech Stack:** Django 5.x, pytest, Cloudflare DNS proxy (Full Strict SSL mode). No new Python packages.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `apps/core/middleware.py` | Add `CloudflareIPMiddleware` class |
| Modify | `config/settings/base.py:42` | Prepend middleware to MIDDLEWARE list |
| Modify | `config/settings/prod.py` | Add `USE_X_FORWARDED_HOST = True` |
| Modify | `deploy/COOLIFY.md` | Add Cloudflare configuration guide section |
| Create | `tests/test_cloudflare_middleware.py` | Unit tests for the new middleware |

---

## Task 1: CloudflareIPMiddleware — TDD

**Files:**
- Create: `tests/test_cloudflare_middleware.py`
- Modify: `apps/core/middleware.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cloudflare_middleware.py`:

```python
import pytest
from django.test import RequestFactory

from apps.core.middleware import CloudflareIPMiddleware


@pytest.fixture
def get_response():
    def _get_response(request):
        from django.http import HttpResponse
        return HttpResponse()
    return _get_response


@pytest.fixture
def middleware(get_response):
    return CloudflareIPMiddleware(get_response)


@pytest.fixture
def factory():
    return RequestFactory()


def test_cf_connecting_ip_overwrites_remote_addr(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "104.16.0.1"  # a CF IP
    request.META["HTTP_CF_CONNECTING_IP"] = "203.0.113.45"  # real user IP

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "203.0.113.45"


def test_no_cf_header_leaves_remote_addr_intact(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    # No HTTP_CF_CONNECTING_IP header

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "192.168.1.1"


def test_empty_cf_header_leaves_remote_addr_intact(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    request.META["HTTP_CF_CONNECTING_IP"] = ""

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "192.168.1.1"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_cloudflare_middleware.py -v
```

Expected: `ImportError` or `AttributeError` — `CloudflareIPMiddleware` doesn't exist yet.

- [ ] **Step 3: Implement `CloudflareIPMiddleware`**

Add to the end of `apps/core/middleware.py` (after `DemoReadOnlyMiddleware`):

```python


class CloudflareIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_ip:
            request.META["REMOTE_ADDR"] = cf_ip
        return self.get_response(request)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_cloudflare_middleware.py -v
```

Expected output:
```
tests/test_cloudflare_middleware.py::test_cf_connecting_ip_overwrites_remote_addr PASSED
tests/test_cloudflare_middleware.py::test_no_cf_header_leaves_remote_addr_intact PASSED
tests/test_cloudflare_middleware.py::test_empty_cf_header_leaves_remote_addr_intact PASSED
3 passed
```

- [ ] **Step 5: Run full test suite to catch regressions**

```bash
uv run pytest --no-cov -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/core/middleware.py tests/test_cloudflare_middleware.py
git commit -m "feat: add CloudflareIPMiddleware to resolve real visitor IP"
```

---

## Task 2: Wire middleware into settings

**Files:**
- Modify: `config/settings/base.py` (line 42 — MIDDLEWARE list)
- Modify: `config/settings/prod.py`

- [ ] **Step 1: Prepend middleware in `config/settings/base.py`**

Current (line 42):
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
```

Change to:
```python
MIDDLEWARE = [
    "apps.core.middleware.CloudflareIPMiddleware",
    "django.middleware.security.SecurityMiddleware",
```

It is safe to include `CloudflareIPMiddleware` in base settings — when `CF-Connecting-IP` is absent (dev, tests) the middleware is a no-op and `REMOTE_ADDR` is untouched.

- [ ] **Step 2: Add `USE_X_FORWARDED_HOST` in `config/settings/prod.py`**

After the `SECURE_PROXY_SSL_HEADER` line (currently line 27), add:

```python
USE_X_FORWARDED_HOST = True
```

This makes `request.get_host()` return the real public domain (e.g. `pipelancer.dabg.dev`) instead of the internal Coolify hostname, which is needed for correct URL generation in emails and redirects.

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest --no-cov -q
```

Expected: all tests pass (middleware is no-op in test env — no CF header present).

- [ ] **Step 4: Commit**

```bash
git add config/settings/base.py config/settings/prod.py
git commit -m "feat: register CloudflareIPMiddleware and set USE_X_FORWARDED_HOST for prod"
```

---

## Task 3: Document Cloudflare dashboard configuration in COOLIFY.md

**Files:**
- Modify: `deploy/COOLIFY.md`

- [ ] **Step 1: Add Cloudflare section to `deploy/COOLIFY.md`**

Append the following section at the end of the file:

```markdown
## Cloudflare Configuration

This app is designed to run behind Cloudflare's proxy. The following settings must be configured in the Cloudflare dashboard.

### SSL/TLS

- **Mode:** Full (Strict)
  - CF validates the origin's Let's Encrypt certificate (managed by Coolify).
- **Always Use HTTPS:** On (Encryption → Edge Certificates → Always Use HTTPS)

### DNS

- A record pointing to your server IP with **Proxy status: Proxied** (orange cloud).
- If you temporarily need to bypass CF (debugging), switch to DNS-only (grey cloud) — HTTPS will still work via Let's Encrypt.

### Cache Rules

Create a Cache Rule to cache static assets at the CF edge:

| Field | Value |
|-------|-------|
| URL pattern | `yourdomain.com/static/*` |
| Cache Level | Cache Everything |
| Edge TTL | 1 month |
| Browser TTL | 1 week |

WhiteNoise already fingerprints static file names (content hash in filename), so cache invalidation is automatic on deploy.

### Security Headers

Django's `SecurityMiddleware` (prod settings) already sends all required security headers:
- `Strict-Transport-Security` (HSTS, 1 year + preload)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`

**Do NOT enable Cloudflare Managed Headers for these** — enabling them alongside Django's headers sends duplicates, which some browsers reject.

### WAF

- **Security Level:** Medium (default)
- **Bot Fight Mode:** On (free tier) — blocks known bots before they hit the origin

### Real Visitor IPs

`CloudflareIPMiddleware` (registered in Django's middleware stack) reads the `CF-Connecting-IP` header and sets it as `REMOTE_ADDR`. This means Django logs, rate limiting, and auth will see the real visitor IP instead of a Cloudflare datacenter IP.

> **Security note:** If someone bypasses Cloudflare and hits the origin directly, they could spoof `CF-Connecting-IP`. To prevent this, configure your server firewall (UFW, iptables, or Coolify network rules) to only accept inbound traffic from [Cloudflare's published IP ranges](https://www.cloudflare.com/ips/).
```

- [ ] **Step 2: Commit**

```bash
git add deploy/COOLIFY.md
git commit -m "docs: add Cloudflare configuration guide to COOLIFY.md"
```

---

## Verification

After deploying to Coolify with Cloudflare proxy active:

```bash
# Confirm real IP appears in Django logs (not a CF datacenter IP like 104.x.x.x)
# Check Coolify → Deployments → View logs and make a request from your browser

# Confirm static assets are cached at CF edge
curl -I https://yourdomain.com/static/css/app.css | grep -i "cf-cache-status"
# Expected: cf-cache-status: HIT (after first request)

# Confirm CSRF still works
# Log in via the browser — no CSRF errors should appear

# Confirm health check still responds
curl https://yourdomain.com/healthz
# Expected: {"status": "ok"}
```
