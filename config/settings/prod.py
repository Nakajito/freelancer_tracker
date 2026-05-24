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

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

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
EMAIL_HOST = "smtp.resend.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "resend"
EMAIL_HOST_PASSWORD = env("RESEND_API_KEY")  # noqa: F405
DEFAULT_FROM_EMAIL = env(  # noqa: F405
    "DEFAULT_FROM_EMAIL", default="noreply@pipelancer.dabg.dev"
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        # Stripe.js required for donate/confirm page
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "font-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
        "frame-src": ["'none'"],
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
