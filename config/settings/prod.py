from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405

if not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS cannot be empty in production")

ALLOWED_HOSTS += ["localhost", "127.0.0.1"]

MIDDLEWARE = ["apps.core.middleware.CloudflareIPMiddleware"] + MIDDLEWARE  # noqa: F405

CSRF_TRUSTED_ORIGINS = [
    o if "://" in o else f"https://{o}"
    for o in env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
]

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Not env-overridable: a stray SECURE_SSL_REDIRECT=False in the Coolify panel
# would silently drop HTTPS enforcement while HSTS stayed on.
SECURE_SSL_REDIRECT = True
# The container healthcheck curls http://localhost:8000/healthz. Without this
# exemption it receives a 301, which `curl -f` treats as success -- so the
# probe passed even when the app was failing.
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp-relay.brevo.com")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_TLS = True
# Without a timeout a hung SMTP connection holds a sync worker for the full
# request timeout, and there are only three workers.
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")  # noqa: F405
DEFAULT_FROM_EMAIL = env(  # noqa: F405
    "DEFAULT_FROM_EMAIL", default="noreply@pipelancer.dabg.dev"
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        # Cloudflare Turnstile CAPTCHA requires challenges.cloudflare.com
        # MP uses redirect flow — no external JS needed on our pages
        "script-src": [
            "'self'",
            "https://challenges.cloudflare.com",
            "https://static.cloudflareinsights.com",
        ],
        "style-src": ["'self'", "'unsafe-inline'"],
        "font-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        # No plugins are used; blocking them removes a legacy XSS vector.
        "object-src": ["'none'"],
        "connect-src": [
            "'self'",
            "https://challenges.cloudflare.com",
            "https://cloudflareinsights.com",
        ],
        "frame-src": ["https://challenges.cloudflare.com"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        # MP uses redirect flow — no iframe or external JS needed
        "form-action": [
            "'self'",
            "https://www.mercadopago.com",
            "https://www.mercadopago.com.ar",
            "https://www.mercadopago.com.br",
            "https://www.mercadopago.com.mx",
            "https://www.mercadopago.cl",
            "https://www.mercadopago.com.co",
        ],
    },
}

# Throttling state must be shared across gunicorn workers. Django's implicit
# default is LocMemCache, which is per-process: with GUNICORN_WORKERS=3 the DRF
# AnonRateThrottle allowed 3x its configured rate and reset on every worker
# recycle. Redis when REDIS_URL is provided, otherwise a database-backed table
# (created by `manage.py createcachetable` in the entrypoint).
REDIS_URL = env("REDIS_URL", default="")  # noqa: F405

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache_table",
        }
    }

WHITENOISE_MAX_AGE = 31_536_000  # 1 year — manifest hashes guarantee invalidation

DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
        "propagate": False,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
