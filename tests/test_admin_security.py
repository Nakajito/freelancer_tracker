"""Security tests for the Django admin site.

Admin is restricted to superusers (not merely staff) via SecureAdminSite,
and its URL is configurable through the ADMIN_URL setting.
"""

import pytest
from django.conf import settings
from django.urls import reverse


def _admin_index_url():
    return reverse("admin:index")


@pytest.mark.django_db
def test_superuser_can_access_admin(client, superuser):
    client.force_login(superuser)
    response = client.get(_admin_index_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_staff_non_superuser_denied(client, staff_user):
    """A user with is_staff=True but is_superuser=False must be denied."""
    client.force_login(staff_user)
    response = client.get(_admin_index_url())
    # Admin redirects unauthorized users to its login page.
    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_normal_user_denied(client, user):
    client.force_login(user)
    response = client.get(_admin_index_url())
    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_anonymous_redirected_to_login(client):
    response = client.get(_admin_index_url())
    assert response.status_code == 302
    assert "login" in response["Location"]


def test_admin_url_setting_default():
    """Default ADMIN_URL keeps the conventional path and a trailing slash."""
    assert settings.ADMIN_URL == "admin/"


@pytest.mark.django_db
def test_admin_index_reverse_resolves(client, superuser):
    """The admin URL is reachable at the path derived from ADMIN_URL."""
    client.force_login(superuser)
    url = _admin_index_url()
    assert url == "/" + settings.ADMIN_URL
    assert client.get(url).status_code == 200
