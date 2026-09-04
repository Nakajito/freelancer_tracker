"""Public informational routes render.

/security was registered in config/urls.py but templates/security.html did not
exist, so the route raised TemplateDoesNotExist and returned 500. No test
covered it.
"""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("name", ["privacy_policy", "terms_of_service", "security"])
def test_public_page_renders(client, name):
    response = client.get(reverse(name))

    assert response.status_code == 200


def test_security_page_links_the_disclosure_channel(client):
    response = client.get(reverse("security"))

    assert b"security@dabg.dev" in response.content
    assert b"/.well-known/security.txt" in response.content


def test_security_txt_is_served(client):
    response = client.get("/.well-known/security.txt")

    assert response.status_code == 200
    assert b"Contact:" in response.content


def test_sitemap_includes_public_pages(client):
    response = client.get("/sitemap.xml")

    assert response.status_code == 200


@pytest.mark.parametrize("url", ["/", "/en/"])
def test_landing_footer_links_security(client, url):
    response = client.get(url, follow=True)

    assert b"/security" in response.content


def test_app_footer_links_security(authed_client):
    from django.urls import reverse as _reverse

    response = authed_client.get(_reverse("dashboard"))

    assert b"/security" in response.content
