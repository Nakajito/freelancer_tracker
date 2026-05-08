from .settings_base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]

MIDDLEWARE = [
    *MIDDLEWARE,
    "allauth.account.middleware.AccountMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

LOGGING["root"]["level"] = "DEBUG"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
