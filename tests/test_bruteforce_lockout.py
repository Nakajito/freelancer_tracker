"""Brute-force lockout holds, and cannot be evaded by spoofing the client IP.

``AXES_ENABLED = False`` in the test settings so ordinary auth tests aren't
throttled, which means nothing else in the suite exercises this path. These
tests re-enable it deliberately.

They assert the security property -- a locked-out attacker cannot authenticate
even with the right password -- rather than a status code. Two layers can block
(django-axes returns 429; allauth's own rate limit re-renders the form as 200),
and which one fires first is an implementation detail that must not make the
guard brittle.
"""

import pytest
from django.test import override_settings
from django.urls import reverse

pytestmark = pytest.mark.django_db

USER_PASSWORD = "testpass123"
OTHER_PASSWORD = "otherpass123"


@pytest.fixture(autouse=True)
def _verified_email(db, user, other_user):
    """ACCOUNT_EMAIL_VERIFICATION is mandatory, so login needs a verified address.

    The conftest fixtures build users straight through the model manager, which
    never creates allauth's EmailAddress row.
    """
    from allauth.account.models import EmailAddress

    for account in (user, other_user):
        EmailAddress.objects.update_or_create(
            user=account,
            email=account.email,
            defaults={"verified": True, "primary": True},
        )


@pytest.fixture(autouse=True)
def _clean_attempts():
    """Reset both throttles between tests.

    allauth's own rate limiter lives in the default cache, which LocMemCache
    keeps for the whole process. Left dirty, it blocks the request before
    ``authenticate()`` runs and axes never sees the attempt at all.
    """
    from django.core.cache import cache

    from axes.models import AccessAttempt

    AccessAttempt.objects.all().delete()
    cache.clear()
    yield
    AccessAttempt.objects.all().delete()
    cache.clear()


def _login(client, email, password, **extra):
    return client.post(
        reverse("account_login"), {"login": email, "password": password}, **extra
    )


def _exhaust(client, email, ip, header_ip=None, attempts=None):
    from django.conf import settings

    for i in range(attempts or settings.AXES_FAILURE_LIMIT + 1):
        extra = {"REMOTE_ADDR": ip}
        if header_ip is not None:
            extra["HTTP_CF_CONNECTING_IP"] = header_ip.format(i=i)
        _login(client, email, "definitely-not-the-password", **extra)


@override_settings(AXES_ENABLED=True, TURNSTILE_ENABLED=False)
def test_correct_password_succeeds_without_lockout(client, user):
    """Control: the assertions below are not vacuous."""
    response = _login(client, user.email, USER_PASSWORD, REMOTE_ADDR="203.0.113.5")

    assert response.wsgi_request.user.is_authenticated


@override_settings(AXES_ENABLED=True, TURNSTILE_ENABLED=False)
def test_lockout_rejects_even_the_correct_password(client, user):
    _exhaust(client, user.email, ip="203.0.113.10")

    response = _login(client, user.email, USER_PASSWORD, REMOTE_ADDR="203.0.113.10")

    assert not response.wsgi_request.user.is_authenticated, (
        "lockout did not hold against the correct password"
    )


@override_settings(AXES_ENABLED=True, TURNSTILE_ENABLED=False)
def test_spoofed_cf_header_cannot_evade_lockout(client, user):
    """Rotating CF-Connecting-IP from an untrusted peer must not reset the count.

    This is the regression guard for CloudflareIPMiddleware's trust boundary:
    the peer is 203.0.113.10 (not a Cloudflare range), so the header is
    discarded and every attempt lands in the same bucket. Without the boundary,
    a fresh header value per request made AXES_FAILURE_LIMIT unreachable.
    """
    _exhaust(client, user.email, ip="203.0.113.10", header_ip="10.0.0.{i}")

    response = _login(
        client,
        user.email,
        USER_PASSWORD,
        REMOTE_ADDR="203.0.113.10",
        HTTP_CF_CONNECTING_IP="10.0.0.250",
    )

    assert not response.wsgi_request.user.is_authenticated, (
        "rotating CF-Connecting-IP evaded the lockout"
    )


@override_settings(AXES_ENABLED=True, TURNSTILE_ENABLED=False)
def test_failed_attempt_is_recorded_against_the_username(client, user):
    """The username dimension of AXES_LOCKOUT_PARAMETERS must carry a value.

    allauth keys its failure signal by a LoginMethod enum member, so the
    previous AXES_USERNAME_FORM_FIELD = "login" resolved to None and the
    lockout silently degraded to IP-only.
    """
    from axes.models import AccessAttempt

    _login(client, user.email, "wrong", REMOTE_ADDR="203.0.113.30")

    attempt = AccessAttempt.objects.get()
    assert attempt.username == user.email.lower()
    assert attempt.ip_address == "203.0.113.30"
