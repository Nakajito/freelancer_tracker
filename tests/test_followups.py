from datetime import date, timedelta

import pytest
from django.urls import reverse

from apps.followups.models import FollowUp
from apps.proposals.models import Client, Proposal, ProposalStatus


@pytest.mark.django_db
class TestFollowUpListView:
    def test_today_in_context(self, authed_client):
        response = authed_client.get(reverse("followup-list"))
        assert response.status_code == 200
        assert response.context["today"] == date.today()

    def test_count_badges(self, authed_client, user, proposal):
        FollowUp.objects.create(
            proposal=proposal,
            description="Up",
            due_date=date.today() + timedelta(days=2),
        )
        FollowUp.objects.create(
            proposal=proposal,
            description="Over",
            due_date=date.today() - timedelta(days=2),
        )
        FollowUp.objects.create(
            proposal=proposal,
            description="Done",
            due_date=date.today(),
            completed=True,
        )
        response = authed_client.get(reverse("followup-list"))
        # Both upcoming and overdue are pending; upcoming() returns all due_date <= cutoff
        assert response.context["upcoming_count"] >= 1
        assert response.context["overdue_count"] == 1
        assert response.context["completed_count"] == 1

    def test_owner_isolation_in_counts(self, authed_client, other_user, proposal):
        from apps.proposals.models import Client, Proposal, ProposalStatus

        other_client = Client.objects.create(owner=other_user, name="Other Co")
        other_proposal = Proposal.objects.create(
            owner=other_user,
            title="Other",
            client=other_client,
            status=ProposalStatus.SENT,
        )
        FollowUp.objects.create(
            proposal=other_proposal,
            description="Other's",
            due_date=date.today(),
        )
        response = authed_client.get(reverse("followup-list"))
        assert response.context["upcoming_count"] == 0
        assert response.context["overdue_count"] == 0


@pytest.mark.django_db
class TestFollowUpCreateView:
    def test_locked_proposal_with_valid_param(self, authed_client, proposal):
        """GET ?proposal=<pk> → 200, locked_proposal in context, form initial set."""
        url = reverse("followup-create") + f"?proposal={proposal.pk}"
        response = authed_client.get(url)
        assert response.status_code == 200
        assert response.context["locked_proposal"] == proposal
        assert response.context["form"].initial["proposal"] == proposal.pk
        assert b'type="hidden"' in response.content
        assert b'name="proposal"' in response.content

    def test_locked_proposal_other_user(self, authed_client, other_user, proposal):
        """GET ?proposal=<pk of other_user's proposal> → locked_proposal is None."""
        other_client = Client.objects.create(owner=other_user, name="Other Co")
        other_proposal = Proposal.objects.create(
            owner=other_user,
            title="Other Proposal",
            client=other_client,
            status=ProposalStatus.SENT,
        )
        url = reverse("followup-create") + f"?proposal={other_proposal.pk}"
        response = authed_client.get(url)
        assert response.status_code == 200
        assert response.context["locked_proposal"] is None

    def test_no_param_no_lock(self, authed_client):
        """GET without ?proposal → locked_proposal is None."""
        response = authed_client.get(reverse("followup-create"))
        assert response.status_code == 200
        assert response.context["locked_proposal"] is None

    def test_post_creates_followup(self, authed_client, proposal):
        """POST valid data → FollowUp created, redirect to followup-list."""
        url = reverse("followup-create")
        data = {
            "proposal": proposal.pk,
            "description": "Check in with client",
            "due_date": (date.today() + timedelta(days=3)).isoformat(),
        }
        response = authed_client.post(url, data)
        assert response.status_code == 302
        assert response["Location"] == reverse("followup-list")
        assert FollowUp.objects.filter(
            proposal=proposal, description="Check in with client"
        ).exists()
