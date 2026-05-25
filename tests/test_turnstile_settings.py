from django.test import RequestFactory, override_settings


def test_turnstile_site_key_in_context(client):
    """turnstile context processor injects TURNSTILE_SITE_KEY into template context."""
    with override_settings(TURNSTILE_SITE_KEY="test-site-key"):
        from apps.accounts.context_processors import turnstile
        request = RequestFactory().get("/")
        ctx = turnstile(request)
        assert ctx["TURNSTILE_SITE_KEY"] == "test-site-key"


def test_turnstile_site_key_missing_returns_empty(client):
    """context processor returns empty string when TURNSTILE_SITE_KEY not set."""
    with override_settings(TURNSTILE_SITE_KEY=""):
        from apps.accounts.context_processors import turnstile
        request = RequestFactory().get("/")
        ctx = turnstile(request)
        assert ctx["TURNSTILE_SITE_KEY"] == ""
