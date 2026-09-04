"""CSRF is actually enforced, and htmx requests carry a token.

Django's test client disables CSRF checking by default, so nothing in the suite
would notice if {% csrf_token %} were dropped from a form or @csrf_exempt were
added to a view. These use enforce_csrf_checks=True.
"""

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def csrf_client(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    return client


def test_post_without_csrf_token_is_rejected(csrf_client, client_model):
    response = csrf_client.post(
        reverse("proposal-create"),
        {"title": "No token", "client": client_model.pk, "amount": "100"},
    )

    assert response.status_code == 403


def test_post_with_csrf_token_is_accepted(csrf_client, client_model):
    """Control: the rejection above is about CSRF, not a broken form."""
    csrf_client.get(reverse("proposal-create"))
    token = csrf_client.cookies["csrftoken"].value

    response = csrf_client.post(
        reverse("proposal-create"),
        {
            "title": "With token",
            "client": client_model.pk,
            "amount": "100",
            "platform": "other",
            "status": "draft",
            "csrfmiddlewaretoken": token,
        },
    )

    assert response.status_code in (200, 302)


def test_htmx_requests_carry_a_csrf_header(authed_client):
    """hx-headers on <body> means any future hx-post is protected by default."""
    response = authed_client.get(reverse("dashboard"))

    assert b"hx-headers" in response.content
    assert b"X-CSRFToken" in response.content


def test_no_view_is_csrf_exempt_except_the_signed_webhook():
    """@csrf_exempt is only defensible where a provider signature replaces it."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "apps"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"csrf_exempt", text) and "donations" not in path.as_posix():
            offenders.append(str(path.relative_to(root)))

    assert offenders == [], f"unexpected csrf_exempt usage: {offenders}"
