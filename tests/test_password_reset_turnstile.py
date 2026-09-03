"""Password reset is CAPTCHA-protected like login and signup.

It mails an arbitrary address on request, so unprotected it is a free outbound
email amplifier against third parties and a cheap way to exhaust the SMTP quota.
"""

from unittest.mock import patch

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_widget_rendered_when_configured(client):
    with override_settings(TURNSTILE_SITE_KEY="test-site-key"):
        response = client.get(reverse("account_reset_password"))

    assert b"cf-turnstile" in response.content
    assert b"challenges.cloudflare.com" in response.content


def test_widget_absent_when_unconfigured(client):
    with override_settings(TURNSTILE_SITE_KEY=""):
        response = client.get(reverse("account_reset_password"))

    assert b"cf-turnstile" not in response.content


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_reset_without_token_sends_no_mail(client, user):
    mail.outbox.clear()

    client.post(reverse("account_reset_password"), {"email": user.email})

    assert mail.outbox == [], "reset mail sent without passing the security check"


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_reset_with_valid_token_sends_mail(client, user):
    from allauth.account.models import EmailAddress

    EmailAddress.objects.update_or_create(
        user=user, email=user.email, defaults={"verified": True, "primary": True}
    )
    mail.outbox.clear()

    with patch("apps.accounts.forms.validate_turnstile", return_value=None):
        client.post(
            reverse("account_reset_password"),
            {"email": user.email, "cf-turnstile-response": "ok"},
        )

    assert len(mail.outbox) == 1, "a legitimate reset was blocked"
