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
        # SITEVERIFY_URL is a fixed https:// module constant; no
        # caller-supplied scheme can reach urlopen here.
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
            result = json.loads(resp.read(4096))
    except urllib.error.URLError:
        logger.warning("Turnstile siteverify network error", exc_info=True)
        _handle_unavailable()
        return
    except ValueError, TypeError:
        # Reached Cloudflare but the body was not the JSON object we expect.
        # Treat as unavailable rather than as a pass.
        logger.error("Turnstile siteverify returned an unparseable body")
        _handle_unavailable()
        return
    except Exception:
        logger.error("Turnstile siteverify unexpected error", exc_info=True)
        _handle_unavailable()
        return

    if not isinstance(result, dict) or not result.get("success"):
        raise ValidationError(_("Security check failed. Please try again."))


def _handle_unavailable() -> None:
    """Decide what an unreachable siteverify endpoint means.

    Failing open turns any degradation of egress to challenges.cloudflare.com --
    or a plain Cloudflare outage -- into a full CAPTCHA bypass on login and
    signup, which is exactly when bot protection matters most. Failing closed is
    the safe default; TURNSTILE_FAIL_OPEN exists as a deliberate, documented
    escape hatch for operators who would rather accept bots than block signups.
    """
    if getattr(settings, "TURNSTILE_FAIL_OPEN", False):
        logger.warning("Turnstile unavailable — failing open per TURNSTILE_FAIL_OPEN")
        return
    raise ValidationError(
        _("Security check is temporarily unavailable. Please try again shortly.")
    )
