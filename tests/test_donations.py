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
        provider=Donation.PROVIDER_MP,
    )
    assert "10.00" in str(d)
    assert "mercadopago" in str(d)


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
    assert b"Mercado Pago" in resp.content
    assert b"Stripe" not in resp.content


@pytest.mark.django_db
def test_donate_confirm_page_renders(client: Client):
    url = reverse("donate_confirm") + "?amount=10&frequency=one_time"
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Mercado Pago" in resp.content
    assert b"donate_mp_preference" not in resp.content  # form action is URL-resolved


# ---------------------------------------------------------------------------
# Mercado Pago create-preference / preapproval views
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

    assert resp.status_code in (302, 301)
    assert "mercadopago.com" in resp["Location"]

    donation = Donation.objects.filter(provider=Donation.PROVIDER_MP).first()
    assert donation is not None
    assert donation.provider_pref_id == "pref_123"
    assert donation.amount == Decimal("25")
    assert donation.frequency == Donation.FREQUENCY_ONE_TIME


@pytest.mark.django_db
def test_mp_create_preapproval_success(client: Client, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "TEST-fake-token"

    mock_sdk = MagicMock()
    mock_sdk.preapproval.return_value.create.return_value = {
        "response": {
            "id": "preapproval_456",
            "init_point": "https://www.mercadopago.com/subscriptions/checkout?preapproval_id=preapproval_456",
        }
    }

    with patch("mercadopago.SDK", return_value=mock_sdk):
        url = reverse("donate_mp_preference")
        resp = client.post(
            url,
            {
                "amount": "10",
                "frequency": "monthly",
                "currency": "ARS",
                "email": "donor@example.com",
            },
        )

    assert resp.status_code in (302, 301)
    assert "mercadopago.com" in resp["Location"]

    donation = Donation.objects.filter(provider=Donation.PROVIDER_MP).first()
    assert donation is not None
    assert donation.provider_pref_id == "preapproval_456"
    assert donation.frequency == Donation.FREQUENCY_MONTHLY
    assert donation.email == "donor@example.com"


@pytest.mark.django_db
def test_mp_preapproval_back_url_uses_public_base(client: Client, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "TEST-token"  # noqa: S105
    settings.MERCADOPAGO_PUBLIC_BASE_URL = "https://pipelancer.example"
    with patch("apps.donations.views.services.create_mp_preapproval") as mock_create:
        mock_create.return_value = {"id": "pa-1", "init_point": "https://mp.test/sub"}
        client.post(
            reverse("donate_mp_preference"),
            {"amount": "200", "frequency": "monthly", "currency": "ARS"},
        )
    back_url = mock_create.call_args.kwargs["back_url"]
    notification_url = mock_create.call_args.kwargs["notification_url"]
    assert back_url.startswith("https://pipelancer.example/")
    assert "localhost" not in back_url
    assert notification_url.startswith("https://pipelancer.example/")


@pytest.mark.django_db
def test_mp_webhook_subscription_authorized(client: Client, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "TEST-fake"

    donation = Donation.objects.create(
        amount=Decimal("10"),
        provider=Donation.PROVIDER_MP,
        frequency=Donation.FREQUENCY_MONTHLY,
    )

    mock_sdk = MagicMock()
    mock_sdk.preapproval.return_value.get.return_value = {
        "response": {
            "id": "preapproval_789",
            "status": "authorized",
            "external_reference": str(donation.pk),
        }
    }

    payload = {"type": "subscription_preapproval", "data": {"id": "preapproval_789"}}

    with patch("mercadopago.SDK", return_value=mock_sdk):
        resp = client.post(
            reverse("donate_webhook_mp"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    assert resp.status_code == 200
    donation.refresh_from_db()
    assert donation.status == Donation.STATUS_COMPLETED
    assert donation.provider_pref_id == "preapproval_789"


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
    donation = Donation.objects.create(
        amount=Decimal("10"), provider=Donation.PROVIDER_MP
    )
    resp = client.get(reverse("donate_success") + f"?donation_id={donation.pk}")
    assert resp.status_code == 200
    assert b"Thank you" in resp.content


@pytest.mark.django_db
def test_donate_failure_page(client: Client):
    donation = Donation.objects.create(
        amount=Decimal("10"), provider=Donation.PROVIDER_MP
    )
    resp = client.get(reverse("donate_failure") + f"?donation_id={donation.pk}")
    assert resp.status_code == 200
    assert b"not completed" in resp.content
