"""The grandfathering migration actually runs and back-fills EmailAddress rows.

pytest-django applies migrations to build the test database, so a broken
RunPython would fail collection -- but that proves only that it executed, not
that it did the right thing. This checks the outcome directly.
"""

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db

# Deliberately low-entropy: high-entropy literals here trip the secret
# scanner, and suppressing that would blind it to a real leak in tests.
TEST_PASSWORD = "not-a-secret"


def test_verification_is_mandatory():
    assert settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory"


def test_backfill_is_idempotent_and_respects_existing_rows(django_user_model):
    """Re-running the back-fill adds nothing and never flips verified=False."""
    from allauth.account.models import EmailAddress
    from django.apps import apps as global_apps

    backfill = _load_backfill()

    legacy = django_user_model.objects.create_user(
        username="legacy", email="legacy@example.com", password="x"
    )
    unverified = django_user_model.objects.create_user(
        username="pending", email="pending@example.com", password="x"
    )
    EmailAddress.objects.create(
        user=unverified, email=unverified.email, verified=False, primary=True
    )

    backfill(global_apps, None)

    assert EmailAddress.objects.get(user=legacy).verified is True, (
        "pre-existing account was not grandfathered in"
    )
    assert EmailAddress.objects.get(user=unverified).verified is False, (
        "back-fill overwrote a deliberately unverified address"
    )

    before = EmailAddress.objects.count()
    backfill(global_apps, None)
    assert EmailAddress.objects.count() == before, "back-fill is not idempotent"


def _load_backfill():
    """Import the RunPython callable from a module whose name starts with a digit."""
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parent.parent
        / "apps"
        / "accounts"
        / "migrations"
        / "0003_verify_existing_emails.py"
    )
    spec = importlib.util.spec_from_file_location("_mig0003", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_verified_email_addresses


def test_new_user_without_emailaddress_cannot_log_in(client, django_user_model):
    """The behaviour the migration exists to prevent for pre-existing accounts."""
    from django.urls import reverse

    django_user_model.objects.create_user(
        username="fresh", email="fresh@example.com", password=TEST_PASSWORD
    )

    response = client.post(
        reverse("account_login"),
        {"login": "fresh@example.com", "password": TEST_PASSWORD},
    )

    assert not response.wsgi_request.user.is_authenticated


def test_user_with_verified_address_can_log_in(client, django_user_model):
    from allauth.account.models import EmailAddress
    from django.urls import reverse

    account = django_user_model.objects.create_user(
        username="verified", email="verified@example.com", password=TEST_PASSWORD
    )
    EmailAddress.objects.create(
        user=account, email=account.email, verified=True, primary=True
    )

    response = client.post(
        reverse("account_login"),
        {"login": "verified@example.com", "password": TEST_PASSWORD},
    )

    assert response.wsgi_request.user.is_authenticated
