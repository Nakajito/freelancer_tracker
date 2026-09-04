import pytest
from django.test import RequestFactory

from apps.core.middleware import CloudflareIPMiddleware


from django.http import HttpResponse


@pytest.fixture
def get_response():
    def _get_response(request):
        return HttpResponse()

    return _get_response


@pytest.fixture
def middleware(get_response):
    return CloudflareIPMiddleware(get_response)


@pytest.fixture
def factory():
    return RequestFactory()


def test_cf_connecting_ip_overwrites_remote_addr(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "104.16.0.1"  # a CF IP
    request.META["HTTP_CF_CONNECTING_IP"] = "203.0.113.45"  # real user IP

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "203.0.113.45"


def test_no_cf_header_leaves_remote_addr_intact(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    # No HTTP_CF_CONNECTING_IP header

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "192.168.1.1"


def test_empty_cf_header_leaves_remote_addr_intact(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    request.META["HTTP_CF_CONNECTING_IP"] = ""

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "192.168.1.1"


def test_whitespace_only_cf_header_leaves_remote_addr_intact(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    request.META["HTTP_CF_CONNECTING_IP"] = "   "

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "192.168.1.1"


# ---------------------------------------------------------------------------
# Trust boundary
#
# The header is only meaningful when the request actually arrived through
# Cloudflare. If the origin is reachable directly, an unvalidated header lets
# any client set REMOTE_ADDR to anything -- which defeats django-axes IP
# lockout (AXES_LOCKOUT_PARAMETERS keys on it), poisons the Turnstile remoteip,
# and forges the IP in every security log line.
# ---------------------------------------------------------------------------


def test_header_from_untrusted_peer_is_ignored(middleware, factory):
    """A direct client spoofing the header must not rewrite REMOTE_ADDR."""
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "203.0.113.99"  # not a Cloudflare address
    request.META["HTTP_CF_CONNECTING_IP"] = "1.2.3.4"  # attacker-chosen

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "203.0.113.99"


def test_header_from_cloudflare_ipv6_peer_is_trusted(middleware, factory):
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "2606:4700::1"
    request.META["HTTP_CF_CONNECTING_IP"] = "203.0.113.45"

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "203.0.113.45"


def test_malformed_header_value_is_ignored(middleware, factory):
    """A trusted peer sending garbage must not poison REMOTE_ADDR."""
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "104.16.0.1"
    request.META["HTTP_CF_CONNECTING_IP"] = "not-an-ip-address"

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "104.16.0.1"


def test_header_list_injection_is_ignored(middleware, factory):
    """Comma-joined values (header smuggling) are not a valid single IP."""
    request = factory.get("/")
    request.META["REMOTE_ADDR"] = "104.16.0.1"
    request.META["HTTP_CF_CONNECTING_IP"] = "1.2.3.4, 5.6.7.8"

    middleware(request)

    assert request.META["REMOTE_ADDR"] == "104.16.0.1"


def test_missing_remote_addr_is_not_trusted(middleware, factory):
    request = factory.get("/")
    request.META.pop("REMOTE_ADDR", None)
    request.META["HTTP_CF_CONNECTING_IP"] = "1.2.3.4"

    middleware(request)

    assert request.META.get("REMOTE_ADDR") != "1.2.3.4"
