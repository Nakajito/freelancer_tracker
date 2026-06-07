# Despliegue en Coolify

## Pre-requisitos

- Cuenta en Coolify
- Repo clonado o conectado a GitHub

## Pasos

### 1. Crear recurso PostgreSQL

1. En Coolify, crear nuevo recurso → PostgreSQL 16
2. Configurar nombre y credenciales
3. Copiar `DATABASE_URL` interno (formato: `postgresql://user:pass@host:5432/db`)

### 2. Crear aplicación

1. Nuevo recurso → Dockerfile
2. Repository: seleccionar repo de freelancer-tracker
3. Branch: main
4. Build context: `.`
5. Dockerfile path: `deploy/Dockerfile`

### 3. Configurar Storage

1. En la app, ir a Settings → Storage
2. Añadir volumen persistente: `/app/media`
3. Esto preserva archivos subidos (imágenes, adjuntos)

> El entrypoint arranca como root, corrige permisos del volumen (`chown app:app /app/media`)
> y luego baja a usuario `app` vía `gosu`. No se necesita configuración extra.

### 4. Environment Variables

Añadir en Settings → Environment:

```
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_urlsafe(50))">
DEBUG=False
ALLOWED_HOSTS=<tu-dominio.com>
CSRF_TRUSTED_ORIGINS=https://<tu-dominio.com>
DATABASE_URL=<del paso 1>
SECURE_SSL_REDIRECT=True
ADMIN_URL=<ruta-secreta>/   # ofusca /admin/, p.ej. panel-7f3a9c/ (incluir la barra final)
GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=60
SEED_DEMO=0
```

> **Admin hardening:** `ADMIN_URL` mueve el panel a una ruta secreta; el admin
> solo admite superusuarios (no staff). django-axes bloquea por IP tras 5
> intentos fallidos (cooloff 1 h). Estos valores se configuran en
> `config/settings/base.py` (`AXES_*`) si se quieren ajustar.

### 5. Configurar Dominio

1. Domain → asignar dominio personalizado
2. Activar HTTPS (Let's Encrypt automático)

### 6. Health Check

1. Health Check Path: `/healthz`
2. Port: `8000`
3. Interval: 30s

### 7. Deploy

1. Click en Deploy
2. Esperar a que termine el build
3. Verificar que /healthz responde {"status":"ok"}

## Verificación post-deploy

```bash
# Health check
curl https://<dominio>/healthz

# Login page
curl -I https://<dominio>/accounts/login/
```

## Troubleshooting

- Si el build falla: verificar DATABASE_URL y DJANGO_SECRET_KEY
- Si 502: verificar que el puerto sea 8000 y health check funcione
- Logs disponibles en Coolify → Deployments → View logs

## Cloudflare Configuration

This app is designed to run behind Cloudflare's proxy. The following settings must be configured in the Cloudflare dashboard.

### SSL/TLS

- **Mode:** Full (Strict)
  - CF validates the origin's Let's Encrypt certificate (managed by Coolify).
- **Always Use HTTPS:** On (Encryption → Edge Certificates → Always Use HTTPS)
  - This redirects at the CF edge, before traffic reaches Django. Django also has `SECURE_SSL_REDIRECT = True` as a second layer — if CF is bypassed, Django still enforces HTTPS.

### DNS

- A record pointing to your server IP with **Proxy status: Proxied** (orange cloud).
- If you temporarily need to bypass CF (debugging), switch to DNS-only (grey cloud) — HTTPS will still work via Let's Encrypt.

### Cache Rules

Create a Cache Rule to cache static assets at the CF edge:

| Field | Value |
|-------|-------|
| URL pattern | `<yourdomain>/static/*` |
| Cache Level | Cache Everything |
| Edge TTL | 1 year |
| Browser TTL | 1 week |

WhiteNoise already fingerprints static file names (content hash in filename), so cache invalidation is automatic on deploy.

Edge TTL matches WhiteNoise's `Cache-Control: max-age` (1 year). Safe because every static file has a content-hash in its filename — a new deploy produces new filenames, immediately bypassing the cache.

### Security Headers

Django's `SecurityMiddleware` and `django-csp` (prod settings) already send all required security headers:
- `Strict-Transport-Security` (HSTS, 1 year + preload)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- `Cross-Origin-Opener-Policy: same-origin`
- `Content-Security-Policy` (managed by `django-csp`)

**Do NOT enable Cloudflare Managed Headers for any of these** — enabling them alongside Django's headers sends duplicates, which some browsers reject.

### WAF

- **Security Level:** Medium (default)
- **Bot Fight Mode:** On (free tier) — blocks known bots before they hit the origin

### Real Visitor IPs

`CloudflareIPMiddleware` (registered in Django's middleware stack) reads the `CF-Connecting-IP` header and sets it as `REMOTE_ADDR`. This means Django logs, rate limiting, and auth will see the real visitor IP instead of a Cloudflare datacenter IP.

> **Security note:** If someone bypasses Cloudflare and hits the origin directly, they could spoof `CF-Connecting-IP`. To prevent this, configure your server firewall (UFW, iptables, or Coolify network rules) to only accept inbound traffic from [Cloudflare's published IP ranges](https://www.cloudflare.com/ips/).
