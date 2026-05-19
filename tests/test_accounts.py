from django.conf import settings
from django.urls import reverse
import pytest


@pytest.mark.django_db
class TestAccountPreferences:
    def test_user_has_profile_preferences(self, user):
        assert user.theme_preference == "system"
        assert user.language_preference == "en"
        assert not user.avatar

    def test_preferences_endpoint_updates_theme_and_language(self, authed_client, user):
        response = authed_client.post(
            reverse("account-preferences"),
            {"theme_preference": "dark", "language_preference": "es"},
            HTTP_REFERER=reverse("dashboard"),
        )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.theme_preference == "dark"
        assert user.language_preference == "es"
        assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == "es"


@pytest.mark.django_db
class TestProfileView:
    def test_profile_renders(self, authed_client):
        response = authed_client.get(reverse("account-profile"))

        assert response.status_code == 200
        assert "form" in response.context
        assert "deactivate_form" in response.context

    def test_profile_updates_user_fields(self, authed_client, user):
        response = authed_client.post(
            reverse("account-profile"),
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "theme_preference": "light",
                "language_preference": "es",
            },
        )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.first_name == "Ada"
        assert user.last_name == "Lovelace"
        assert user.email == "ada@example.com"
        assert user.theme_preference == "light"
        assert user.language_preference == "es"


@pytest.mark.django_db
class TestDeactivateAccountView:
    def test_deactivate_requires_valid_password(self, authed_client, user):
        response = authed_client.post(
            reverse("account-deactivate"),
            {"password": "wrong-password"},
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is True

    def test_deactivate_marks_user_inactive_and_logs_out(self, authed_client, user):
        response = authed_client.post(
            reverse("account-deactivate"),
            {"password": "testpass123"},
        )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.is_active is False
        assert "_auth_user_id" not in authed_client.session


def test_i18n_settings_are_configured():
    assert ("en", "English") in settings.LANGUAGES
    assert ("es", "Español") in settings.LANGUAGES
    middleware = list(settings.MIDDLEWARE)
    assert "django.middleware.locale.LocaleMiddleware" in middleware
    assert (
        middleware.index("django.contrib.sessions.middleware.SessionMiddleware")
        < middleware.index("django.middleware.locale.LocaleMiddleware")
        < middleware.index("django.middleware.common.CommonMiddleware")
    )
