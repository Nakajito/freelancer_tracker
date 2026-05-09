from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]  # noqa: F405

MIDDLEWARE = [
    *MIDDLEWARE,  # noqa: F405
    "allauth.account.middleware.AccountMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

LOGGING["root"]["level"] = "DEBUG"  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
