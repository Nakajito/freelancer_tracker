import json
import logging
import urllib.parse
import urllib.request
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def validate_turnstile(token: str, remote_ip: str = "") -> None:
    if not getattr(settings, "TURNSTILE_ENABLED", False):
        return

    if not token:
        raise ValidationError(_("Please complete the security check."))

    payload: dict[str, str] = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(SITEVERIFY_URL, data=data)
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
    except Exception:
        logger.warning(
            "Turnstile siteverify request failed — failing open", exc_info=True
        )
        return

    if not result.get("success"):
        raise ValidationError(_("Security check failed. Please try again."))
