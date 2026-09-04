"""CSRF is actually enforced, and htmx requests carry a token.

Django's test client disables CSRF checking by default, so nothing in the suite
would notice if {% csrf_token %} were dropped from a form or @csrf_exempt were
added to a view. These use enforce_csrf_checks=True.
"""

import json
import re

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
    """hx-headers on <body> means any future hx-post is protected by default.

    Asserts the exact, well-formed attribute rather than bare substrings.
    A prior version of this test only checked that "hx-headers" and
    "X-CSRFToken" appeared *somewhere* in the response -- which would have
    stayed green even with an unterminated hx-headers='...">  attribute that
    swallows the rest of the page as its value, or a Django {# #} comment
    directly above <body> that leaked as literal text because it spanned two
    lines (Django's {# #} tokenizer cannot cross a newline). Both shipped to
    production at once; neither would have failed this test as it was
    originally written.
    """
    response = authed_client.get(reverse("dashboard"))
    body = response.content.decode()

    match = re.search(r'<body[^>]*\bhx-headers=([\'"])(.*?)\1[^>]*>', body)
    assert match, f"no well-formed hx-headers attribute found on <body>: {body[:500]!r}"

    hx_headers = json.loads(match.group(2))
    token = hx_headers.get("X-CSRFToken", "")
    # Django masks the token per-request, so comparing to a fixed value would
    # be flaky; a real csrf_token render is a long non-empty string, whereas
    # an unrendered {{ csrf_token }} (e.g. autoescape gone wrong) is not.
    assert len(token) > 20, f"hx-headers X-CSRFToken looks unrendered: {token!r}"

    # No unprocessed Django template syntax should ever reach the client.
    assert "{#" not in body
    assert "{%" not in body


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
