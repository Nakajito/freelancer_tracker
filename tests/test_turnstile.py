import json
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import translation

from apps.accounts.turnstile import validate_turnstile


@override_settings(TURNSTILE_ENABLED=False)
def test_disabled_skips_validation():
    # Must not raise even with empty token
    validate_turnstile("", "")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_empty_token_raises():
    with translation.override("en"):
        with pytest.raises(ValidationError, match="complete the security check"):
            validate_turnstile("", "1.2.3.4")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_valid_token_passes():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"success": True}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        validate_turnstile("valid-token", "1.2.3.4")  # must not raise


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_invalid_token_raises():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"success": False}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with translation.override("en"):
            with pytest.raises(ValidationError, match="Security check failed"):
                validate_turnstile("bad-token", "1.2.3.4")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_url_error_fails_open():
    """Transient network errors (URLError) fail open without raising."""
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        validate_turnstile("any-token", "1.2.3.4")  # must not raise


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_unexpected_error_fails_open():
    """Unexpected exceptions (bad JSON, etc.) fail open without raising."""
    with patch("urllib.request.urlopen", side_effect=RuntimeError("unexpected")):
        validate_turnstile("any-token", "1.2.3.4")  # must not raise


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="")
def test_missing_secret_key_raises():
    """Empty secret key raises ValidationError (fail closed, not fail open)."""
    with pytest.raises(ValidationError):
        validate_turnstile("valid-token", "1.2.3.4")


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
def test_no_remote_ip_omits_remoteip_field():
    """remoteip is optional — must work when empty."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"success": True}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        validate_turnstile("token", "")
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = urllib.parse.parse_qs(req.data.decode())
        assert "remoteip" not in body
