from pathlib import Path

import environ
import dj_database_url

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-key-change-in-prod")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Obfuscated admin path. Default keeps the conventional "admin/" for dev/tests;
# production sets a secret value via the ADMIN_URL env var. Always trailing-slash.
ADMIN_URL = env("ADMIN_URL", default="admin/").lstrip("/")
if not ADMIN_URL.endswith("/"):
    ADMIN_URL += "/"

INSTALLED_APPS = [
    "apps.core.admin_apps.SecureAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "rest_framework",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "apps.core",
    "apps.accounts",
    "apps.proposals",
    "apps.followups",
    "apps.timetracking",
    "apps.templates_app",
    "apps.dashboard",
    "apps.exports",
    "apps.donations",
    "axes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.core.middleware.DemoReadOnlyMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # AxesMiddleware must be LAST so it sees the final authenticated request.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.preferences",
                "apps.accounts.context_processors.turnstile",
                "apps.core.context_processors.demo_mode",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = env("DATABASE_URL", default="")

if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("es", "Español"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

AUTH_USER_MODEL = "accounts.User"

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    # AxesStandaloneBackend must be FIRST to short-circuit locked-out attempts.
    "axes.backends.AxesStandaloneBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# django-axes — brute-force lockout
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
# The identifier field is 'login' in allauth POST data, but its failure
# signal keys credentials by a LoginMethod enum member -- one form field
# cannot cover both, so resolution is delegated to a callable.
AXES_USERNAME_CALLABLE = "apps.accounts.axes_username.get_username"
# Lock on the pair, not on the IP alone: IP-only lockout is defeated by anyone
# with a handful of addresses and simultaneously lets one abuser lock out every
# legitimate user behind a shared NAT. Locking the (ip, username) combination
# still stops credential stuffing against a single account when the source IP
# rotates. See CloudflareIPMiddleware for how REMOTE_ADDR is established.
AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]
AXES_RESET_ON_SUCCESS = True

# Cloudflare's published edge ranges (https://www.cloudflare.com/ips/).
# Only requests whose peer address falls inside one of these may set
# REMOTE_ADDR via the CF-Connecting-IP header. Override via env when fronted by
# a different proxy; set empty to never trust the header.
CLOUDFLARE_IP_RANGES = env.list(
    "CLOUDFLARE_IP_RANGES",
    default=[
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22",
        "2400:cb00::/32",
        "2606:4700::/32",
        "2803:f800::/32",
        "2405:b500::/32",
        "2405:8100::/32",
        "2a06:98c0::/29",
        "2c0f:f248::/32",
    ],
)

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Email is the sole login identifier, so an unverified address is an unproven
# identity. allauth defaults to "optional", which let anyone sign up under
# somebody else's address and use the account.
ACCOUNT_EMAIL_VERIFICATION = env(  # noqa: F405
    "ACCOUNT_EMAIL_VERIFICATION", default="mandatory"
)
# allauth's default is already True; pin it so a future upgrade cannot silently
# turn login/reset responses into an account-existence oracle.
ACCOUNT_PREVENT_ENUMERATION = True

# Declared explicitly rather than inherited: these throttle the flows that send
# mail to arbitrary addresses. Backed by the shared cache (see prod CACHES).
ACCOUNT_RATE_LIMITS = {
    "login": "10/m/ip",
    "login_failed": "5/5m/key",
    "signup": "5/m/ip",
    "reset_password": "3/m/ip,3/h/key",
    "reset_password_from_key": "10/m/ip",
    "confirm_email": "3/m/key",
    "change_password": "5/m/user",
}

ACCOUNT_FORMS = {
    "login": "apps.accounts.forms.TurnstileLoginForm",
    "signup": "apps.accounts.forms.TurnstileSignupForm",
    "reset_password": "apps.accounts.forms.TurnstileResetPasswordForm",
}

TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
TURNSTILE_ENABLED = env.bool("TURNSTILE_ENABLED", default=False)
# When Cloudflare's siteverify endpoint is unreachable, reject the attempt
# rather than waving it through. Set True only if blocking signups during a
# Cloudflare outage is worse for you than admitting bots during one.
TURNSTILE_FAIL_OPEN = env.bool("TURNSTILE_FAIL_OPEN", default=False)

LOGIN_REDIRECT_URL = "dashboard"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"
DEMO_USER_EMAIL = "demo@propotrack.test"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # The browsable API renderer ships an HTML forms UI and renders exception
    # detail for every /api/ endpoint. Nothing here is meant to be explored by
    # hand, so serve JSON only.
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "120/min",
    },
}

# Argon2 first (modern, memory-hard), then Django defaults for legacy hashes.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Payment providers
MERCADOPAGO_ACCESS_TOKEN = env("MERCADOPAGO_ACCESS_TOKEN", default="")
MERCADOPAGO_PUBLIC_KEY = env("MERCADOPAGO_PUBLIC_KEY", default="")
# ISO currency matching your MP account's country (ARS, BRL, MXN, CLP, COP, PEN, UYU…)
MERCADOPAGO_CURRENCY = env("MERCADOPAGO_CURRENCY", default="MXN")
# Public base URL (e.g. https://abc.ngrok.io) for MP callbacks when the request
# host is not publicly reachable (local dev behind localhost). MP rejects
# non-public back_urls; the monthly/preapproval flow requires a valid back_url.
MERCADOPAGO_PUBLIC_BASE_URL = env("MERCADOPAGO_PUBLIC_BASE_URL", default="")
# HMAC secret from the MP dashboard (Webhooks -> signature). Without it the
# webhook rejects every request rather than trusting unsigned callers.
MERCADOPAGO_WEBHOOK_SECRET = env("MERCADOPAGO_WEBHOOK_SECRET", default="")
MERCADOPAGO_WEBHOOK_TOLERANCE_SECONDS = env.int(
    "MERCADOPAGO_WEBHOOK_TOLERANCE_SECONDS", default=15 * 60
)

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
    },
}
