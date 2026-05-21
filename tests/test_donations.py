import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.donations.models import Donation
from apps.donations.services import validate_donation_amount


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_donation_str():
    d = Donation.objects.create(
        amount=Decimal("10.00"),
        currency="USD",
        provider=Donation.PROVIDER_STRIPE,
    )
    assert "10.00" in str(d)
    assert "stripe" in str(d)


@pytest.mark.django_db
def test_donation_default_status():
    d = Donation.objects.create(
        amount=Decimal("5.00"),
        provider=Donation.PROVIDER_MP,
    )
    assert d.status == Donation.STATUS_PENDING


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------


def test_validate_amount_custom_wins():
    result = validate_donation_amount(Decimal("10"), Decimal("25"))
    assert result == Decimal("25")


def test_validate_amount_tier_used_when_no_custom():
    result = validate_donation_amount(Decimal("10"), None)
    assert result == Decimal("10")


def test_validate_amount_zero_raises():
    with pytest.raises(ValueError):
        validate_donation_amount(Decimal("0"), None)


def test_validate_amount_none_raises():
    with pytest.raises(ValueError):
        validate_donation_amount(None, None)


# ---------------------------------------------------------------------------
# Donate page (GET)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_donate_page_renders(client: Client):
    url = reverse("donate")
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Stripe" in resp.content
    assert b"Mercado Pago" in resp.content


@pytest.mark.django_db
def test_donate_confirm_page_renders(client: Client):
    url = reverse("donate_confirm") + "?amount=10&frequency=one_time&method=stripe"
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"stripe-payment-element" in resp.content


# ---------------------------------------------------------------------------
# Stripe create-intent view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stripe_create_intent_no_key(client: Client, settings):
    settings.STRIPE_SECRET_KEY = ""
    url = reverse("donate_stripe_intent")
    resp = client.post(url, {"amount": "10", "frequency": "one_time"})
    assert resp.status_code == 503


@pytest.mark.django_db
def test_stripe_create_intent_invalid_amount(client: Client, settings):
    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    url = reverse("donate_stripe_intent")
    resp = client.post(url, {"amount": "abc"})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_stripe_create_intent_success(client: Client, settings):
    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    settings.STRIPE_PUBLIC_KEY = "pk_test_fake"

    mock_intent = MagicMock()
    mock_intent.client_secret = "pi_test_secret_xyz"

    with patch("apps.donations.services.stripe.PaymentIntent.create", return_value=mock_intent):
        url = reverse("donate_stripe_intent")
        resp = client.post(url, {"amount": "10", "frequency": "one_time"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["client_secret"] == "pi_test_secret_xyz"
    assert "donation_id" in data

    donation = Donation.objects.get(pk=data["donation_id"])
    assert donation.status == Donation.STATUS_PENDING
    assert donation.provider == Donation.PROVIDER_STRIPE
    assert donation.amount == Decimal("10")


# ---------------------------------------------------------------------------
# Mercado Pago create-preference view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mp_create_preference_no_key(client: Client, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = ""
    url = reverse("donate_mp_preference")
    resp = client.post(url, {"amount": "10", "frequency": "one_time"})
    assert resp.status_code == 503


@pytest.mark.django_db
def test_mp_create_preference_success(client: Client, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "TEST-fake-token"

    mock_sdk = MagicMock()
    mock_sdk.preference.return_value.create.return_value = {
        "response": {
            "id": "pref_123",
            "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=pref_123",
        }
    }

    with patch("mercadopago.SDK", return_value=mock_sdk):
        url = reverse("donate_mp_preference")
        resp = client.post(
            url,
            {"amount": "25", "frequency": "one_time", "currency": "ARS"},
        )

    # Should redirect to MP init_point
    assert resp.status_code in (302, 301)
    assert "mercadopago.com" in resp["Location"]

    donation = Donation.objects.filter(provider=Donation.PROVIDER_MP).first()
    assert donation is not None
    assert donation.provider_pref_id == "pref_123"
    assert donation.amount == Decimal("25")


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stripe_webhook_invalid_signature(client: Client, settings):
    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = "whsec_fake"

    import stripe as stripe_lib

    with patch(
        "apps.donations.services.stripe.Webhook.construct_event",
        side_effect=stripe_lib.SignatureVerificationError("bad sig", "sig_header"),
    ):
        resp = client.post(
            reverse("donate_webhook_stripe"),
            data=b'{"type":"payment_intent.succeeded"}',
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad",
        )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_stripe_webhook_payment_succeeded(client: Client, settings):
    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = "whsec_fake"

    donation = Donation.objects.create(
        amount=Decimal("10"),
        provider=Donation.PROVIDER_STRIPE,
    )

    fake_event = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_123",
                "metadata": {"donation_id": str(donation.pk)},
            }
        },
    }

    with patch(
        "apps.donations.services.stripe.Webhook.construct_event",
        return_value=fake_event,
    ):
        resp = client.post(
            reverse("donate_webhook_stripe"),
            data=json.dumps(fake_event).encode(),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

    assert resp.status_code == 200
    donation.refresh_from_db()
    assert donation.status == Donation.STATUS_COMPLETED
    assert donation.provider_payment_id == "pi_test_123"


# ---------------------------------------------------------------------------
# Mercado Pago webhook (IPN)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mp_webhook_approved(client: Client, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "TEST-fake"

    donation = Donation.objects.create(
        amount=Decimal("25"),
        provider=Donation.PROVIDER_MP,
    )

    mock_sdk = MagicMock()
    mock_sdk.payment.return_value.get.return_value = {
        "response": {
            "id": 987,
            "status": "approved",
            "external_reference": str(donation.pk),
        }
    }

    payload = {"type": "payment", "data": {"id": "987"}}

    with patch("mercadopago.SDK", return_value=mock_sdk):
        resp = client.post(
            reverse("donate_webhook_mp"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    assert resp.status_code == 200
    donation.refresh_from_db()
    assert donation.status == Donation.STATUS_COMPLETED
    assert donation.provider_payment_id == "987"


# ---------------------------------------------------------------------------
# Success / Failure pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_donate_success_page(client: Client):
    donation = Donation.objects.create(amount=Decimal("10"), provider=Donation.PROVIDER_STRIPE)
    resp = client.get(reverse("donate_success") + f"?donation_id={donation.pk}")
    assert resp.status_code == 200
    assert b"Thank you" in resp.content


@pytest.mark.django_db
def test_donate_failure_page(client: Client):
    donation = Donation.objects.create(amount=Decimal("10"), provider=Donation.PROVIDER_MP)
    resp = client.get(reverse("donate_failure") + f"?donation_id={donation.pk}")
    assert resp.status_code == 200
    assert b"not completed" in resp.content
