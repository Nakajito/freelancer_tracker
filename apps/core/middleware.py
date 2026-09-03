import ipaddress
import logging

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
                _(
                    "This feature is disabled in demo mode. Create an account to use it."
                ),
            )
            referer = request.META.get("HTTP_REFERER", "")
            return redirect(referer or reverse("dashboard"))
        return self.get_response(request)


logger = logging.getLogger("django.security")


class CloudflareIPMiddleware:
    """Rewrite ``REMOTE_ADDR`` from ``CF-Connecting-IP``, but only when the
    request genuinely came from Cloudflare.

    ``REMOTE_ADDR`` is the key django-axes locks out on
    (``AXES_LOCKOUT_PARAMETERS``) and the value DRF's ``AnonRateThrottle``
    buckets by. Trusting the header unconditionally therefore hands any client
    that can reach the origin directly a way to rotate its identity per request
    and slip every one of those controls, while writing an attacker-chosen IP
    into the security log. So the peer address is checked against Cloudflare's
    published ranges first, and the header value must parse as a single IP.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._trusted = tuple(
            ipaddress.ip_network(net)
            for net in getattr(settings, "CLOUDFLARE_IP_RANGES", ())
        )

    def _peer_is_cloudflare(self, remote_addr: str) -> bool:
        if not remote_addr or not self._trusted:
            return False
        try:
            peer = ipaddress.ip_address(remote_addr)
        except ValueError:
            return False
        return any(peer in net for net in self._trusted)

    def __call__(self, request):
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
        if cf_ip and self._peer_is_cloudflare(request.META.get("REMOTE_ADDR", "")):
            try:
                ipaddress.ip_address(cf_ip)
            except ValueError:
                logger.warning(
                    "Discarding malformed CF-Connecting-IP from trusted peer %s",
                    request.META.get("REMOTE_ADDR"),
                )
            else:
                request.META["REMOTE_ADDR"] = cf_ip
        return self.get_response(request)
