from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

_SAFE_METHODS = frozenset(["GET", "HEAD", "OPTIONS"])
_DEMO_ALLOWED_PATHS = frozenset(["/i18n/setlang/"])


class DemoReadOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method not in _SAFE_METHODS
            and request.path not in _DEMO_ALLOWED_PATHS
            and getattr(request, "user", None)
            and request.user.is_authenticated
            and request.user.email == settings.DEMO_USER_EMAIL
        ):
            messages.info(
                request,
                _("This feature is disabled in demo mode. Create an account to use it."),
            )
            referer = request.META.get("HTTP_REFERER", "")
            return redirect(referer or reverse("dashboard"))
        return self.get_response(request)
