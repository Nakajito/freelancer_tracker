"""Redirect targets are validated and query params cannot 500 the app."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Open redirect
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "https://evil.test/phish",
        "//evil.test/phish",
        "http://evil.test",
        "https://example.com@evil.test/",
    ],
)
def test_preferences_does_not_redirect_off_site(authed_client, hostile):
    response = authed_client.post(
        reverse("account-preferences"),
        {"language_preference": "es"},
        HTTP_REFERER=hostile,
    )

    assert response.status_code == 302
    assert "evil.test" not in response["Location"], (
        f"open redirect via Referer: {response['Location']}"
    )


def test_preferences_still_honours_a_same_site_referer(authed_client):
    response = authed_client.post(
        reverse("account-preferences"),
        {"language_preference": "es"},
        HTTP_REFERER="http://testserver/en/proposals/",
    )

    assert response.status_code == 302
    assert "/proposals/" in response["Location"]


def test_demo_middleware_does_not_redirect_off_site(client, db, settings):
    """The demo account's blocked writes bounce off the Referer too."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    demo = User.objects.create_user(
        username="demo", email=settings.DEMO_USER_EMAIL, password="demo1234"
    )
    client.force_login(demo)

    response = client.post(
        reverse("proposal-create"),
        {"title": "x"},
        HTTP_REFERER="https://evil.test/phish",
    )

    assert response.status_code == 302
    assert "evil.test" not in response["Location"]


# ---------------------------------------------------------------------------
# Query-parameter robustness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "?year=abc",
        "?month=13",
        "?month=0",
        "?year=9999",
        "?year=-1",
        "?quarter=99",
        "?half=7",
        "?period=monthly&month=99",
        "?year=99999999999999999999",
        "?month=",
    ],
)
def test_monthly_summary_survives_hostile_params(authed_client, query):
    response = authed_client.get(reverse("monthly-summary") + query)

    assert response.status_code == 200, f"{query} produced {response.status_code}"
