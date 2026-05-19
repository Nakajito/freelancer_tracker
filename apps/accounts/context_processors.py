from django.utils import translation


def preferences(request):
    user = getattr(request, "user", None)
    theme = "system"
    language = translation.get_language() or "en"

    if user and user.is_authenticated:
        theme = getattr(user, "theme_preference", "system")
        language = getattr(user, "language_preference", language)

    return {
        "active_theme": theme,
        "active_language": language,
    }
