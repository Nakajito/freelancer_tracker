import json
import logging
import urllib.error
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

    secret = getattr(settings, "TURNSTILE_SECRET_KEY", "")
    if not secret:
        raise ValidationError(_("Security check unavailable. Please contact support."))

    payload: dict[str, str] = {
        "secret": secret,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            SITEVERIFY_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read(4096))
    except urllib.error.URLError:
        logger.warning(
            "Turnstile siteverify network error — failing open", exc_info=True
        )
        return
    except Exception:
        logger.error(
            "Turnstile siteverify unexpected error — failing open", exc_info=True
        )
        return

    if not result.get("success"):
        raise ValidationError(_("Security check failed. Please try again."))
