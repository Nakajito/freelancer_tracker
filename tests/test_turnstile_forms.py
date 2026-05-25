"""
Tests for TurnstileFormMixin using a stub parent form.

We test the mixin in isolation — not through LoginForm/SignupForm — because
allauth's LoginForm.clean() hits the DB to authenticate, which would mask
whether validate_turnstile() is called at all.
"""
from unittest.mock import patch

import pytest
from django import forms as dj_forms
from django.test import RequestFactory, override_settings

from apps.accounts.forms import TurnstileFormMixin


class _StubForm(dj_forms.Form):
    """Minimal form whose clean() returns {} without side effects."""
    def clean(self):
        return {}


class _MixinForm(TurnstileFormMixin, _StubForm):
    """Concrete form using the mixin with a neutral parent."""
    pass


@pytest.fixture
def factory():
    return RequestFactory()


@override_settings(TURNSTILE_ENABLED=False)
def test_mixin_disabled_skips_validate(factory):
    """TURNSTILE_ENABLED=False → validate_turnstile is still called but no-ops."""
    request = factory.post("/", {"cf-turnstile-response": ""})
    form = _MixinForm(data=request.POST)
    form.request = request  # simulate LoginForm behaviour

    with patch("apps.accounts.forms.validate_turnstile") as mock_vt:
        mock_vt.return_value = None
        form.clean()

    mock_vt.assert_called_once_with("", request.META["REMOTE_ADDR"])


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_mixin_passes_token_and_ip(factory):
    """Token and REMOTE_ADDR are forwarded to validate_turnstile."""
    request = factory.post("/", {"cf-turnstile-response": "tok"}, REMOTE_ADDR="5.5.5.5")
    form = _MixinForm(data=request.POST)
    form.request = request

    with patch("apps.accounts.forms.validate_turnstile") as mock_vt:
        mock_vt.return_value = None
        form.clean()

    mock_vt.assert_called_once_with("tok", "5.5.5.5")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_mixin_no_request_passes_empty_ip():
    """When self.request is absent (SignupForm case), remote_ip is ''."""
    form = _MixinForm(data={"cf-turnstile-response": "tok"})
    # No form.request set — mimics SignupForm which doesn't receive request kwarg

    with patch("apps.accounts.forms.validate_turnstile") as mock_vt:
        mock_vt.return_value = None
        form.clean()

    mock_vt.assert_called_once_with("tok", "")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_mixin_missing_token_calls_validate_with_empty(factory):
    """Missing cf-turnstile-response → validate called with '' (it raises ValidationError)."""
    from django.core.exceptions import ValidationError

    request = factory.post("/", {})  # no cf-turnstile-response key
    form = _MixinForm(data=request.POST)
    form.request = request

    with patch("apps.accounts.forms.validate_turnstile", side_effect=ValidationError("check")):
        with pytest.raises(ValidationError):
            form.clean()
