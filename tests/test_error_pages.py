"""Error pages must render with locally-served CSS, not the Tailwind CDN.

Production CSP (`script-src 'self'`) blocks `cdn.tailwindcss.com`, so any
error template depending on the CDN renders unstyled. These tests guard the
404/500 templates against regressing back to external CDN assets.
"""

from pathlib import Path

import pytest
from django.template.loader import render_to_string
from django.test import Client

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


@pytest.mark.django_db
def test_404_uses_local_css_not_cdn(settings):
    settings.DEBUG = False
    client = Client(raise_request_exception=False)

    response = client.get("/this-path-does-not-exist/")

    assert response.status_code == 404
    body = response.content.decode()
    assert "css/app.css" in body
    assert "cdn.tailwindcss.com" not in body
    assert "fonts.googleapis.com" not in body


@pytest.mark.parametrize("template", ["404.html", "500.html"])
def test_error_template_has_no_cdn_reference(template):
    source = (TEMPLATES_DIR / template).read_text()

    assert "cdn.tailwindcss.com" not in source
    assert "fonts.googleapis.com" not in source


def test_500_renders_with_local_css():
    rendered = render_to_string("500.html")

    assert "css/app.css" in rendered
    assert "cdn.tailwindcss.com" not in rendered
