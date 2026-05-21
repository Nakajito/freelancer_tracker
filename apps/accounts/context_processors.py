from django.utils import translation


def preferences(request):
    user = getattr(request, "user", None)
    language = translation.get_language() or "en"

    if user and user.is_authenticated:
        language = getattr(user, "language_preference", language)

    return {
        "active_language": language,
    }
