"""Cross-user access control at the HTTP layer.

Per-user isolation is enforced by ``OwnerQuerysetMixin`` /
``ProposalOwnerQuerysetMixin`` (``apps/core/mixins.py``). Every other ownership
test in this suite stops at the queryset or the context dict, so dropping a
mixin from a view is a silent, green-CI vulnerability. These tests assert the
observable outcome instead: user A asking for user B's object gets a 404.

Add a row to ``OWNED_ROUTES`` whenever a new owner-scoped detail/edit/delete
route is added.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.followups.models import FollowUp
from apps.proposals.models import Client, Proposal, ProposalStatus
from apps.templates_app.models import ProposalTemplate
from apps.timetracking.models import RecurringRetainer, TimeEntry


@pytest.fixture
def victim_objects(db, other_user):
    """A full set of domain objects owned by ``other_user``."""
    client_obj = Client.objects.create(owner=other_user, name="Victim Client")
    proposal = Proposal.objects.create(
        owner=other_user,
        title="Victim Proposal",
        client=client_obj,
        status=ProposalStatus.ACCEPTED,
        amount=Decimal("5000"),
        sent_date=date.today(),
    )
    return {
        "client": client_obj,
        "proposal": proposal,
        "template": ProposalTemplate.objects.create(
            owner=other_user,
            name="Victim Template",
            body="Confidential rate card: ${amount}",
        ),
        "followup": FollowUp.objects.create(
            proposal=proposal,
            description="Victim follow-up",
            due_date=date.today() + timedelta(days=3),
        ),
        "timeentry": TimeEntry.objects.create(
            proposal=proposal, date=date.today(), hours=Decimal("2.00")
        ),
        "retainer": RecurringRetainer.objects.create(
            proposal=proposal, monthly_hours=Decimal("10.00")
        ),
    }


# (url_name, key into victim_objects, http_method)
OWNED_ROUTES = [
    ("proposal-detail", "proposal", "get"),
    ("proposal-update", "proposal", "get"),
    ("proposal-delete", "proposal", "get"),
    ("proposal-delete", "proposal", "post"),
    ("client-delete", "client", "get"),
    ("client-delete", "client", "post"),
    ("template-detail", "template", "get"),
    ("template-update", "template", "get"),
    ("template-preview", "template", "get"),
    ("template-use", "template", "get"),
    ("template-delete", "template", "get"),
    ("template-delete", "template", "post"),
    ("followup-complete", "followup", "post"),
    ("followup-delete", "followup", "get"),
    ("followup-delete", "followup", "post"),
    ("timeentry-update", "timeentry", "get"),
    ("timeentry-delete", "timeentry", "get"),
    ("timeentry-delete", "timeentry", "post"),
]


@pytest.mark.parametrize(
    "url_name,obj_key,method",
    OWNED_ROUTES,
    ids=[f"{n}-{m}" for n, _, m in OWNED_ROUTES],
)
def test_other_users_object_is_not_reachable(
    authed_client, victim_objects, url_name, obj_key, method
):
    """User A must get 404 for user B's object — never 200, never a redirect."""
    obj = victim_objects[obj_key]
    url = reverse(url_name, kwargs={"pk": obj.pk})

    response = getattr(authed_client, method)(url)

    assert response.status_code == 404, (
        f"{url_name} ({method.upper()}) leaked another user's "
        f"{obj_key} (pk={obj.pk}): got {response.status_code}"
    )


@pytest.mark.parametrize(
    "url_name,obj_key,method",
    OWNED_ROUTES,
    ids=[f"{n}-{m}" for n, _, m in OWNED_ROUTES],
)
def test_owned_object_is_reachable(
    client, user, victim_objects, url_name, obj_key, method
):
    """Control: the same routes work for the object's real owner.

    Without this, a view that 404s unconditionally would pass the test above.
    """
    client.force_login(user)
    obj = victim_objects[obj_key]
    obj_owner = getattr(obj, "owner", None) or obj.proposal.owner

    client.force_login(obj_owner)
    url = reverse(url_name, kwargs={"pk": obj.pk})

    response = getattr(client, method)(url)

    assert response.status_code in (200, 302), (
        f"{url_name} ({method.upper()}) denied the legitimate owner: "
        f"got {response.status_code}"
    )


def test_destructive_routes_do_not_delete_other_users_data(
    authed_client, victim_objects
):
    """A denied delete must not have side effects."""
    proposal = victim_objects["proposal"]
    template = victim_objects["template"]

    authed_client.post(reverse("proposal-delete", kwargs={"pk": proposal.pk}))
    authed_client.post(reverse("template-delete", kwargs={"pk": template.pk}))

    assert Proposal.objects.filter(pk=proposal.pk).exists()
    assert ProposalTemplate.objects.filter(pk=template.pk).exists()
