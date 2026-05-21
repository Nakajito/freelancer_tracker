import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

DEMO_EMAIL = "demo@propotrack.test"
DEMO_PASSWORD = "demo1234"


@pytest.fixture
def demo_user(db):
    return User.objects.create_user(
        username="demo",
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD,
        first_name="Demo",
    )


@pytest.fixture
def demo_client(client, demo_user):
    client.force_login(demo_user)
    return client


# ---------------------------------------------------------------------------
# DemoAutoLoginView
# ---------------------------------------------------------------------------


def test_demo_auto_login_redirects_to_dashboard(client, demo_user):
    url = reverse("demo-login")
    response = client.get(url)
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")


def test_demo_auto_login_logs_in_as_demo_user(client, demo_user):
    client.get(reverse("demo-login"))
    # Session should have _auth_user_id set
    from django.contrib.auth import SESSION_KEY
    assert SESSION_KEY in client.session


def test_demo_auto_login_already_authenticated_redirects(authed_client):
    response = authed_client.get(reverse("demo-login"))
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")


def test_demo_auto_login_no_user_redirects_to_landing(client, db):
    # No demo user created — should redirect to landing
    response = client.get(reverse("demo-login"))
    assert response.status_code == 302
    assert response["Location"] == reverse("landing")


# ---------------------------------------------------------------------------
# DemoReadOnlyMiddleware
# ---------------------------------------------------------------------------


def test_demo_middleware_blocks_post(demo_client):
    url = reverse("proposal-create")
    response = demo_client.post(url, data={})
    assert response.status_code == 302


def test_demo_middleware_passes_get(demo_client):
    url = reverse("dashboard")
    response = demo_client.get(url)
    assert response.status_code == 200


def test_demo_middleware_allows_set_language(demo_client):
    response = demo_client.post("/i18n/setlang/", data={"language": "es", "next": "/"})
    # Django's set_language redirects on success (302)
    assert response.status_code == 302


def test_demo_middleware_does_not_block_normal_user_post(authed_client):
    # Normal user POST to proposal-create should NOT be blocked by middleware
    # (it may fail validation, but middleware lets it through → not a 302 from middleware)
    url = reverse("proposal-create")
    response = authed_client.post(url, data={})
    # Form validation failure returns 200 (re-render with errors), not redirect
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Context processor
# ---------------------------------------------------------------------------


def test_is_demo_true_in_context_for_demo_user(demo_client):
    response = demo_client.get(reverse("dashboard"))
    assert response.context["is_demo"] is True


def test_is_demo_false_in_context_for_normal_user(authed_client):
    response = authed_client.get(reverse("dashboard"))
    assert response.context["is_demo"] is False


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------


def test_landing_ver_demo_links_to_demo_login(client, db):
    response = client.get(reverse("landing"))
    assert response.status_code == 200
    content = response.content.decode()
    demo_url = reverse("demo-login")
    assert demo_url in content


# ---------------------------------------------------------------------------
# DemoExitView
# ---------------------------------------------------------------------------


def test_demo_exit_logs_out_and_redirects_to_landing(demo_client):
    response = demo_client.get(reverse("demo-exit"))
    assert response.status_code == 302
    assert response["Location"] == reverse("landing")


def test_demo_exit_unauthenticated_redirects_to_landing(client, db):
    response = client.get(reverse("demo-exit"))
    assert response.status_code == 302
    assert response["Location"] == reverse("landing")
