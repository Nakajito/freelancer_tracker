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
GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=60
SEED_DEMO=0
```

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