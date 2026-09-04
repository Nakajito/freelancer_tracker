"""DonateSuccessView reconciles a still-pending donation against Mercado Pago.

MP's webhook is asynchronous and can arrive after the donor's browser redirect
lands here, so without this the success page could show "Pending" forever with
no path to ever update -- get_mp_donation_status() existed for exactly this
and was, until now, never called anywhere in the codebase.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import signing
from django.urls import reverse

from apps.donations.models import Donation

pytestmark = pytest.mark.django_db


def _token(donation: Donation) -> str:
    return signing.dumps({"pk": donation.pk}, salt="donations.callback")


@pytest.fixture
def pending_donation():
    return Donation.objects.create(
        amount=Decimal("25.00"),
        provider=Donation.PROVIDER_MP,
        status=Donation.STATUS_PENDING,
    )


def test_pending_donation_is_promoted_to_completed(client, pending_donation):
    with patch(
        "apps.donations.views.services.get_mp_donation_status", return_value="approved"
    ) as mock_status:
        response = client.get(
            reverse("donate_success") + f"?t={_token(pending_donation)}"
        )

    mock_status.assert_called_once_with(pending_donation.pk)
    pending_donation.refresh_from_db()
    assert pending_donation.status == Donation.STATUS_COMPLETED
    assert response.context["donation"].status == Donation.STATUS_COMPLETED


@pytest.mark.parametrize("mp_status", ["rejected", "cancelled"])
def test_pending_donation_is_demoted_to_failed(client, pending_donation, mp_status):
    with patch(
        "apps.donations.views.services.get_mp_donation_status",
        return_value=mp_status,
    ):
        client.get(reverse("donate_success") + f"?t={_token(pending_donation)}")

    pending_donation.refresh_from_db()
    assert pending_donation.status == Donation.STATUS_FAILED


def test_pending_donation_stays_pending_when_mp_agrees(client, pending_donation):
    with patch(
        "apps.donations.views.services.get_mp_donation_status", return_value="pending"
    ):
        client.get(reverse("donate_success") + f"?t={_token(pending_donation)}")

    pending_donation.refresh_from_db()
    assert pending_donation.status == Donation.STATUS_PENDING


def test_already_completed_donation_is_not_reconciled(client):
    """No point re-querying MP for a donation that already has a final status."""
    donation = Donation.objects.create(
        amount=Decimal("25.00"),
        provider=Donation.PROVIDER_MP,
        status=Donation.STATUS_COMPLETED,
    )

    with patch("apps.donations.views.services.get_mp_donation_status") as mock_status:
        client.get(reverse("donate_success") + f"?t={_token(donation)}")

    mock_status.assert_not_called()


def test_mp_lookup_failure_does_not_break_the_page(client, pending_donation):
    """A network error talking to MP must not turn the success page into a 500."""
    with patch(
        "apps.donations.views.services.get_mp_donation_status",
        side_effect=Exception("MP unreachable"),
    ):
        response = client.get(
            reverse("donate_success") + f"?t={_token(pending_donation)}"
        )

    assert response.status_code == 200
    pending_donation.refresh_from_db()
    assert pending_donation.status == Donation.STATUS_PENDING


def test_failure_view_does_not_reconcile(client, pending_donation):
    """Reconciliation is only wired on the success page."""
    with patch("apps.donations.views.services.get_mp_donation_status") as mock_status:
        client.get(reverse("donate_failure") + f"?t={_token(pending_donation)}")

    mock_status.assert_not_called()
