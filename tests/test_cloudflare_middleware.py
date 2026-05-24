import pytest
from django.test import RequestFactory

from apps.core.middleware import CloudflareIPMiddleware


@pytest.fixture
def get_response():
    def _get_response(request):
        from django.http import HttpResponse
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
