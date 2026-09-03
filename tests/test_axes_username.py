"""The axes username resolver handles both of axes' calling conventions."""

import pytest
from django.test import RequestFactory

from apps.accounts.axes_username import get_username


@pytest.fixture
def factory():
    return RequestFactory()


def test_credentials_with_allauth_enum_key(factory):
    """allauth sends LoginMethod.EMAIL, a str subclass, as the dict key."""
    from allauth.account.app_settings import LoginMethod

    request = factory.post("/")
    credentials = {LoginMethod.EMAIL: "User@Example.com", "password": "x"}

    assert get_username(request, credentials) == "user@example.com"


def test_credentials_with_plain_login_key(factory):
    request = factory.post("/")
    assert (
        get_username(request, {"login": "Someone@Example.com"}) == "someone@example.com"
    )


def test_falls_back_to_allauth_post_field(factory):
    """The pre-auth lockout check passes no credentials."""
    request = factory.post("/", {"login": "Victim@Example.com", "password": "x"})
    assert get_username(request, None) == "victim@example.com"


def test_falls_back_to_admin_post_field(factory):
    request = factory.post("/", {"username": "admin", "password": "x"})
    assert get_username(request, None) == "admin"


def test_absent_identifier_is_none(factory):
    request = factory.post("/", {"password": "x"})
    assert get_username(request, None) is None


def test_empty_credentials_falls_through_to_post(factory):
    request = factory.post("/", {"login": "fallback@example.com"})
    assert get_username(request, {}) == "fallback@example.com"
