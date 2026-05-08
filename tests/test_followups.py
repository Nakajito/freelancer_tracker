from datetime import date, timedelta

import pytest
from django.urls import reverse

from apps.followups.models import FollowUp


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
