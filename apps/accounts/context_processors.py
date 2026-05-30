from django.utils import translation


def preferences(request):
    user = getattr(request, "user", None)
    language = translation.get_language() or "en"

    if user and user.is_authenticated:
        language = getattr(user, "language_preference", language)

    return {
        "active_language": language,
    }


def turnstile(request):
    from django.conf import settings

    return {
        "TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", ""),
    }
