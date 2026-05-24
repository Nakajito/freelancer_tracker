# Cloudflare DNS + Proxy Integration

**Date:** 2026-05-24  
**Status:** Approved  
**Scope:** Configure Django + deploy stack to work correctly behind Cloudflare proxy

---

## Context

App runs on Coolify via Docker (gunicorn :8000). Cloudflare is already the DNS provider with the domain registered. SSL mode: Full (Strict) — CF validates the origin's Let's Encrypt cert.

Django already has `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` set in `prod.py`. CSRF and ALLOWED_HOSTS are configured via env vars.

---

## Architecture

```
Browser ──HTTPS──▶ Cloudflare (proxy, CDN, DDoS, SSL termination)
                        │
                   Full Strict SSL (validates Let's Encrypt on origin)
                        │
                   ──HTTPS──▶ Coolify/Gunicorn :8000
                                   │
                              Django middleware stack
                              └─ CloudflareIPMiddleware  (new, position: first)
                                   │ overwrites REMOTE_ADDR with CF-Connecting-IP
                              └─ SecurityMiddleware
                              └─ ... (rest unchanged)
```

---

## Components

### 1. `apps/core/middleware.py` — `CloudflareIPMiddleware`

New middleware. Reads `CF-Connecting-IP` header (set by Cloudflare on every proxied request) and overwrites `REMOTE_ADDR` so Django sees the real visitor IP in logs, auth, and rate limiting.

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

**Position in stack:** Before `SecurityMiddleware` (index 0) so all downstream middleware and views see the correct IP.

### 2. `config/settings/prod.py` — additions

```python
USE_X_FORWARDED_HOST = True  # request.get_host() returns real domain, not internal Coolify host
```

Add `CloudflareIPMiddleware` as first entry in `MIDDLEWARE` (prod only, via prod.py override or prepend).

### 3. `deploy/COOLIFY.md` — new section: "Cloudflare Configuration"

Document required Cloudflare dashboard settings:

**SSL/TLS:**
- Mode: Full (Strict)
- Always Use HTTPS: On

**Cache Rules** (for static assets):
- URL pattern: `tusitio.com/static/*`
- Cache Level: Cache Everything
- Edge TTL: 1 month
- Browser TTL: 1 week

**Managed Headers** (free, toggle on):
- `Strict-Transport-Security` (HSTS)
- `X-Content-Type-Options: nosniff`
- Note: `X-Frame-Options` already sent by Django's `XFrameOptionsMiddleware` — leave CF's toggle off to avoid duplication

**WAF:**
- Security Level: Medium (default)
- Bot Fight Mode: On (free tier)

**DNS:**
- A record → origin server IP, proxy status: Proxied (orange cloud)

### 4. `tests/test_middleware.py`

```python
def test_cf_connecting_ip_overwrites_remote_addr():
    # CF header present → REMOTE_ADDR replaced
    ...

def test_no_cf_header_leaves_remote_addr_intact():
    # No CF header → REMOTE_ADDR unchanged
    ...
```

---

## What Does NOT Change

| Setting | Status |
|---|---|
| `SECURE_PROXY_SSL_HEADER` | Already correct in prod.py |
| `SECURE_SSL_REDIRECT` | Already correct |
| `CSPMiddleware` | Already in stack, CF doesn't interfere |
| `CSRF_TRUSTED_ORIGINS` | Already via env var |
| `ALLOWED_HOSTS` | Already via env var |

---

## Security Note

`CF-Connecting-IP` can be spoofed if a request bypasses Cloudflare and reaches the origin directly. Mitigation (out of scope for this integration, document as recommendation): configure Coolify/server firewall to only accept traffic from [Cloudflare IP ranges](https://www.cloudflare.com/ips/).

---

## Out of Scope

- Cloudflare Tunnel (not needed with Full Strict SSL)
- Cloudflare R2 for media storage
- Cloudflare Workers
- Firewall-level IP allowlisting (server config, not app config)
