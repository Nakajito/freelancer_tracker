from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.conf import settings

from .models import Donation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mercado Pago
# ---------------------------------------------------------------------------


def create_mp_preference(
    donation: Donation, back_urls: dict[str, str], notification_url: str
) -> dict[str, Any]:
    import mercadopago  # local import — optional dep

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    frequency_label = (
        "mensual" if donation.frequency == Donation.FREQUENCY_MONTHLY else "única"
    )
    preference_data: dict[str, Any] = {
        "items": [
            {
                "title": f"Donación a Pipelancer ({frequency_label})",
                "quantity": 1,
                "unit_price": float(donation.amount),
                "currency_id": donation.currency,
            }
        ],
        "back_urls": back_urls,
        "auto_return": "approved",
        "notification_url": notification_url,
        "external_reference": str(donation.pk),
        "statement_descriptor": "Pipelancer",
    }

    result = sdk.preference().create(preference_data)
    response: dict[str, Any] = result["response"]
    return response


def handle_mp_webhook(data: dict[str, Any]) -> None:
    import mercadopago  # local import

    topic = data.get("type") or data.get("topic", "")
    resource_id = data.get("data", {}).get("id") or data.get("id")

    if topic not in ("payment", "merchant_order") or not resource_id:
        return

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
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
        logger.info("MP donation %s completed (payment=%s)", donation_id, mp_payment_id)
    elif mp_status in ("rejected", "cancelled"):
        Donation.objects.filter(pk=donation_id).update(
            status=Donation.STATUS_FAILED,
            provider_payment_id=mp_payment_id,
        )
        logger.warning("MP donation %s failed (status=%s)", donation_id, mp_status)


def get_mp_donation_status(donation_id: int) -> str | None:
    """Query MP for the latest payment status of a donation by external_reference."""
    import mercadopago

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    result = sdk.payment().search({"external_reference": str(donation_id)})
    payments = result.get("response", {}).get("results", [])
    if payments:
        return str(payments[0].get("status"))
    return None


def validate_donation_amount(amount: Decimal | None, custom: Decimal | None) -> Decimal:
    value = custom if custom else amount
    if not value or value <= 0:
        raise ValueError("Invalid donation amount")
    return value
