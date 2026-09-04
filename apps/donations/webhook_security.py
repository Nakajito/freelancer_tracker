"""Mercado Pago webhook signature verification.

MP signs notifications with an HMAC-SHA256 over a fixed manifest:

    id:<data.id>;request-id:<x-request-id>;ts:<ts>;

where ``ts`` and ``v1`` arrive in the ``x-signature`` header as
``ts=<unix-seconds>,v1=<hex digest>``. The key is the webhook secret from the
MP dashboard.

Without this the endpoint is an unauthenticated trigger for outbound MP API
calls with any resource id the caller invents, and a replayed genuine
cancellation notice can flip a donation back to failed.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time

from django.conf import settings
from django.http import HttpRequest

logger = logging.getLogger("django.security")

# How far out of date a signature may be. MP retries for a while, so this has
# to tolerate real delays without leaving replays useful indefinitely.
DEFAULT_TOLERANCE_SECONDS = 15 * 60


class WebhookVerificationError(Exception):
    """The request did not carry a valid, fresh MP signature."""


def _parse_signature_header(raw: str) -> tuple[str, str]:
    """Return ``(ts, v1)`` from ``ts=...,v1=...``; raise if either is missing."""
    parts: dict[str, str] = {}
    for chunk in raw.split(","):
        key, _, value = chunk.partition("=")
        key = key.strip()
        if key:
            parts[key] = value.strip()

    ts, v1 = parts.get("ts", ""), parts.get("v1", "")
    if not ts or not v1:
        raise WebhookVerificationError("x-signature is missing ts or v1")
    return ts, v1


def verify_mp_webhook(request: HttpRequest, data_id: str) -> None:
    """Raise ``WebhookVerificationError`` unless the request is authentic.

    ``data_id`` is the resource id the notification refers to; it is part of
    the signed manifest, so a valid signature for one resource cannot be
    replayed against another.
    """
    secret = getattr(settings, "MERCADOPAGO_WEBHOOK_SECRET", "")
    if not secret:
        raise WebhookVerificationError(
            "MERCADOPAGO_WEBHOOK_SECRET is not configured; refusing to trust webhook"
        )

    signature = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")
    if not signature:
        raise WebhookVerificationError("missing x-signature header")

    ts, received = _parse_signature_header(signature)

    try:
        age = abs(time.time() - int(ts))
    except ValueError as exc:
        raise WebhookVerificationError("x-signature ts is not an integer") from exc

    tolerance = getattr(
        settings, "MERCADOPAGO_WEBHOOK_TOLERANCE_SECONDS", DEFAULT_TOLERANCE_SECONDS
    )
    if age > tolerance:
        raise WebhookVerificationError(f"signature is stale ({age:.0f}s old)")

    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received):
        raise WebhookVerificationError("signature mismatch")
