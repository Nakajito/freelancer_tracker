"""Security properties of the donations flow.

Donations are anonymous records with no owner, so the usual OwnerQuerysetMixin
pattern does not apply -- the callback pages and the provider webhook each need
their own authentication story.
"""

import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest
from django.core import signing
from django.urls import reverse

from apps.donations.models import Donation
from apps.donations.services import validate_donation_amount

pytestmark = pytest.mark.django_db

SECRET = "test-webhook-secret"


@pytest.fixture
def donation():
    return Donation.objects.create(
        amount=Decimal("25.00"),
        provider=Donation.PROVIDER_MP,
        email="donor@example.com",
    )


def _sign(data_id: str, request_id: str = "req-1", ts: str | None = None) -> dict:
    ts = ts or str(int(time.time()))
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {"HTTP_X_SIGNATURE": f"ts={ts},v1={v1}", "HTTP_X_REQUEST_ID": request_id}


# ---------------------------------------------------------------------------
# Callback pages — no raw pk enumeration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("route", ["donate_success", "donate_failure"])
def test_raw_pk_no_longer_resolves_a_donation(client, donation, route):
    """?donation_id=N used to enumerate amount, provider and status for every row."""
    response = client.get(reverse(route) + f"?donation_id={donation.pk}")

    assert response.status_code == 200
    assert "donation" not in response.context, "raw pk still resolves a donation"
    assert b"25.00" not in response.content
    assert b"donor@example.com" not in response.content


@pytest.mark.parametrize("route", ["donate_success", "donate_failure"])
def test_signed_token_resolves_the_donation(client, donation, route):
    token = signing.dumps({"pk": donation.pk}, salt="donations.callback")

    response = client.get(reverse(route) + f"?t={token}")

    assert response.status_code == 200
    assert response.context["donation"].pk == donation.pk


@pytest.mark.parametrize("route", ["donate_success", "donate_failure"])
def test_forged_token_is_rejected(client, donation, route):
    forged = signing.dumps({"pk": donation.pk}, salt="wrong-salt")

    response = client.get(reverse(route) + f"?t={forged}")

    assert response.status_code == 404


def test_expired_token_is_rejected(client, donation, monkeypatch):
    """Callback links are short-lived, so a leaked URL stops working."""
    token = signing.dumps({"pk": donation.pk}, salt="donations.callback")
    monkeypatch.setattr("apps.donations.views.DONATION_TOKEN_MAX_AGE", -1)

    response = client.get(reverse("donate_success") + f"?t={token}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Webhook — signature required
# ---------------------------------------------------------------------------


def _post(client, payload, **extra):
    return client.post(
        reverse("donate_webhook_mp"),
        data=json.dumps(payload),
        content_type="application/json",
        **extra,
    )


def test_unsigned_webhook_is_rejected(client, settings):
    settings.MERCADOPAGO_WEBHOOK_SECRET = SECRET

    response = _post(client, {"type": "payment", "data": {"id": "1"}})

    assert response.status_code == 401


def test_bad_signature_is_rejected(client, settings):
    settings.MERCADOPAGO_WEBHOOK_SECRET = SECRET

    response = _post(
        client,
        {"type": "payment", "data": {"id": "1"}},
        HTTP_X_SIGNATURE="ts=1700000000,v1=deadbeef",
        HTTP_X_REQUEST_ID="req-1",
    )

    assert response.status_code == 401


def test_stale_signature_is_rejected(client, settings):
    """Replaying a genuine notification must stop working once it ages out."""
    settings.MERCADOPAGO_WEBHOOK_SECRET = SECRET
    old_ts = str(int(time.time()) - 60 * 60)

    response = _post(
        client,
        {"type": "payment", "data": {"id": "1"}},
        **_sign("1", ts=old_ts),
    )

    assert response.status_code == 401


def test_signature_is_bound_to_the_resource_id(client, settings):
    """A signature valid for one resource must not authorise another."""
    settings.MERCADOPAGO_WEBHOOK_SECRET = SECRET

    response = _post(
        client,
        {"type": "payment", "data": {"id": "999"}},
        **_sign("111"),
    )

    assert response.status_code == 401


def test_unconfigured_secret_refuses_rather_than_trusts(client, settings):
    """A missing secret must not degrade into accepting everything."""
    settings.MERCADOPAGO_WEBHOOK_SECRET = ""

    response = _post(client, {"type": "payment", "data": {"id": "1"}}, **_sign("1"))

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Amount validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["Infinity", "-Infinity", "1E+100", "0", "-5", "0.001"])
def test_out_of_range_amounts_are_rejected(raw):
    with pytest.raises(ValueError):
        validate_donation_amount(Decimal(raw), None)


def test_valid_amount_is_quantized():
    assert validate_donation_amount(Decimal("25.005"), None) == Decimal("25.00")


def test_custom_amount_takes_precedence():
    assert validate_donation_amount(Decimal("10"), Decimal("50")) == Decimal("50.00")
