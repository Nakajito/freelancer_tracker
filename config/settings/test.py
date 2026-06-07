from .base import *  # noqa: F401, F403

DEBUG = True

MIDDLEWARE = [
    *MIDDLEWARE,  # noqa: F405
    "allauth.account.middleware.AccountMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable brute-force lockout so auth tests aren't throttled.
AXES_ENABLED = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

LOGGING["root"]["level"] = "CRITICAL"  # noqa: F405
