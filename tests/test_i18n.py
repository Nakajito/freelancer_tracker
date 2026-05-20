"""i18n routing, language-switching, and translation tests."""

import pytest
from django.utils import translation
from django.urls import reverse


# ---------------------------------------------------------------------------
# 1. Language switcher redirects to prefixed URL
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_set_language_es_redirects_to_prefixed_url(client):
    """set_language POST redirects user to /es/ prefixed URL."""
    response = client.post(
        reverse("set_language"),
        {"language": "es", "next": "/en/dashboard/"},
        HTTP_REFERER="http://testserver/en/dashboard/",
    )
    assert response.status_code == 302
    assert "/es/" in response["Location"]


# ---------------------------------------------------------------------------
# 2. Machine routes accessible without language prefix
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_healthz_no_prefix(client):
    """healthz endpoint is reachable at bare path (no language prefix)."""
    response = client.get("/healthz")
    assert response.status_code == 200


@pytest.mark.django_db
def test_robots_no_prefix(client):
    """robots.txt is reachable at bare path (no language prefix)."""
    response = client.get("/robots.txt")
    assert response.status_code == 200


@pytest.mark.django_db
def test_sitemap_no_prefix(client):
    """sitemap.xml is reachable at bare path (no language prefix)."""
    response = client.get("/sitemap.xml")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 3. ProposalStatus enum labels translate under translation.override
# ---------------------------------------------------------------------------


def test_proposal_status_translates_to_es():
    """ProposalStatus labels translate correctly under Spanish locale."""
    from apps.proposals.models import ProposalStatus

    with translation.override("es"):
        assert str(ProposalStatus.DRAFT.label) != "Draft"  # should be 'Borrador'
        assert str(ProposalStatus.ACCEPTED.label) != "Accepted"  # should be 'Aceptada'


# ---------------------------------------------------------------------------
# 4. UI routes return 200 with language prefix (authenticated)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_en_dashboard_accessible(authed_client):
    """Authenticated user can reach /en/dashboard/."""
    response = authed_client.get("/en/dashboard/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_es_dashboard_accessible(authed_client):
    """Authenticated user can reach /es/dashboard/."""
    response = authed_client.get("/es/dashboard/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 5. reverse() returns language-prefixed URLs
# ---------------------------------------------------------------------------


def test_reverse_returns_prefixed_url():
    """reverse() includes language prefix when i18n_patterns are active."""
    with translation.override("en"):
        url = reverse("dashboard")
        assert url.startswith("/en/")

    with translation.override("es"):
        url = reverse("dashboard")
        assert url.startswith("/es/")
