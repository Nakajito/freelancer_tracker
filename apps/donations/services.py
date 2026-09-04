from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from django.conf import settings

from .models import Donation

logger = logging.getLogger(__name__)


def _is_public_url(url: str) -> bool:
    """MP requires public HTTPS URLs for back_urls, notification_url, auto_return."""
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname not in (
        "localhost",
        "127.0.0.1",
    )


# ---------------------------------------------------------------------------
# Mercado Pago — one-time
# ---------------------------------------------------------------------------


def create_mp_preference(
    donation: Donation, back_urls: dict[str, str], notification_url: str
) -> dict[str, Any]:
    import mercadopago  # local import — optional dep

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    currency = getattr(settings, "MERCADOPAGO_CURRENCY", donation.currency)
    preference_data: dict[str, Any] = {
        "items": [
            {
                "title": "Donación única a Pipelancer",
                "quantity": 1,
                "unit_price": float(donation.amount),
                "currency_id": currency,
            }
        ],
        "external_reference": str(donation.pk),
        "statement_descriptor": "Pipelancer",
    }
    if _is_public_url(back_urls.get("success", "")):
        preference_data["back_urls"] = back_urls
        preference_data["auto_return"] = "approved"
    if _is_public_url(notification_url):
        preference_data["notification_url"] = notification_url
    if donation.email:
        preference_data["payer"] = {"email": donation.email}

    result = sdk.preference().create(preference_data)
    response: dict[str, Any] = result["response"]
    return response


# ---------------------------------------------------------------------------
# Mercado Pago — recurring (preapproval / subscription)
# ---------------------------------------------------------------------------


def create_mp_preapproval(
    donation: Donation, back_url: str, notification_url: str
) -> dict[str, Any]:
    """Create a monthly recurring subscription via MP Preapproval API."""
    import mercadopago

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    currency = getattr(settings, "MERCADOPAGO_CURRENCY", donation.currency)
    preapproval_data: dict[str, Any] = {
        "reason": "Donación mensual a Pipelancer",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": float(donation.amount),
            "currency_id": currency,
        },
        "external_reference": str(donation.pk),
        "back_url": back_url,
    }
    if _is_public_url(notification_url):
        preapproval_data["notification_url"] = notification_url
    if donation.email:
        preapproval_data["payer_email"] = donation.email

    result = sdk.preapproval().create(preapproval_data)
    response: dict[str, Any] = result["response"]
    return response


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


def handle_mp_webhook(data: dict[str, Any]) -> None:
    import mercadopago

    topic = data.get("type") or data.get("topic", "")
    resource_id = data.get("data", {}).get("id") or data.get("id")

    if not resource_id:
        return

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    # Subscription lifecycle (authorized → completed; cancelled/paused → failed)
    if topic == "subscription_preapproval":
        pa_info = sdk.preapproval().get(resource_id)
        pa = pa_info.get("response", {})
        donation_id = pa.get("external_reference")
        pa_status = pa.get("status")

        if not donation_id:
            return

        if pa_status == "authorized":
            Donation.objects.filter(pk=donation_id).update(
                status=Donation.STATUS_COMPLETED,
                provider_pref_id=str(resource_id),
            )
            logger.info(
                "MP subscription %s authorized for donation %s",
                resource_id,
                donation_id,
            )
        elif pa_status in ("cancelled", "paused"):
            Donation.objects.filter(pk=donation_id).update(
                status=Donation.STATUS_FAILED,
            )
            logger.warning(
                "MP subscription %s %s for donation %s",
                resource_id,
                pa_status,
                donation_id,
            )
        return

    # Individual payment (one-time or recurring charge)
    if topic not in ("payment", "merchant_order"):
        return

    payment_info = sdk.payment().get(resource_id)
    payment = payment_info.get("response", {})

    donation_id = payment.get("external_reference")
    mp_status = payment.get("status")
    mp_payment_id = str(payment.get("id", ""))

    if not donation_id:
        return

    if mp_status == "approved":
        Donation.objects.filter(pk=donation_id).update(
            status=Donation.STATUS_COMPLETED,
            provider_payment_id=mp_payment_id,
        )
        logger.info(
            "MP payment %s approved for donation %s", mp_payment_id, donation_id
        )
    elif mp_status in ("rejected", "cancelled"):
        Donation.objects.filter(pk=donation_id).update(
            status=Donation.STATUS_FAILED,
            provider_payment_id=mp_payment_id,
        )
        logger.warning(
            "MP payment %s failed (status=%s) for donation %s",
            mp_payment_id,
            mp_status,
            donation_id,
        )


def get_mp_donation_status(donation_id: int) -> str | None:
    """Query MP for the latest payment status of a donation by external_reference."""
    import mercadopago

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    result = sdk.payment().search({"external_reference": str(donation_id)})
    payments = result.get("response", {}).get("results", [])
    if payments:
        return str(payments[0].get("status"))
    return None


# Donation.amount is numeric(10,2): anything larger overflows the column.
MIN_DONATION_AMOUNT = Decimal("1")
MAX_DONATION_AMOUNT = Decimal("1000000")


def validate_donation_amount(amount: Decimal | None, custom: Decimal | None) -> Decimal:
    """Return a clean, storable amount or raise ``ValueError``.

    ``value <= 0`` alone was not enough: ``Decimal("Infinity")`` and
    ``Decimal("1E+100")`` both pass it, then overflow the column and reach
    ``float()`` on the way to Mercado Pago as a non-serializable ``inf``.
    """
    value = custom if custom else amount
    if value is None:
        raise ValueError("Invalid donation amount")
    if not value.is_finite():
        raise ValueError("Donation amount must be a finite number")
    if value < MIN_DONATION_AMOUNT or value > MAX_DONATION_AMOUNT:
        raise ValueError(
            f"Donation amount must be between {MIN_DONATION_AMOUNT} "
            f"and {MAX_DONATION_AMOUNT}"
        )
    return value.quantize(Decimal("0.01"))
