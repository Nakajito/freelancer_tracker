from decimal import Decimal
from datetime import date, timedelta

import pytest

from apps.proposals.models import Proposal, ProposalStatus, Tag
from apps.templates_app.models import ProposalTemplate
from apps.templates_app.services import PlaceholderRenderer
from apps.followups.models import FollowUp
from apps.timetracking.models import TimeEntry


@pytest.mark.django_db
class TestProposalTemplateModel:
    def test_create_template(self, user):
        template = ProposalTemplate.objects.create(
            owner=user,
            name="Standard Contract",
            body="Hello {client}, we would like to work on {project} for {amount}.",
        )
        assert template.name == "Standard Contract"

    def test_template_with_placeholders(self, user):
        template = ProposalTemplate.objects.create(
            owner=user,
            name="With Placeholders",
            body="{client} - {project} - ${amount}",
            placeholders={"amount": "decimal"},
        )
        assert template.placeholders is not None


@pytest.mark.django_db
class TestPlaceholderRenderer:
    def test_render_basic(self, user):
        result = PlaceholderRenderer.render(
            "Hello ${client}!", {"client": "Acme Corp", "project": "Website"}
        )
        assert "Acme Corp" in result

    def test_render_with_date(self, user):
        result = PlaceholderRenderer.render(
            "Date: ${date}", {"client": "Acme", "date": "2026-01-15"}
        )
        assert "2026-01-15" in result

    def test_extract_placeholders(self):
        placeholders = PlaceholderRenderer.extract_placeholders(
            "Hello ${client}, amount is ${amount}"
        )
        assert "client" in placeholders
        assert "amount" in placeholders

    def test_build_context(self):
        ctx = PlaceholderRenderer.build_context(
            client_name="Acme", project_title="Website", amount="1500"
        )
        assert ctx["client"] == "Acme"
        assert ctx["project"] == "Website"
        assert ctx["amount"] == "1500"
        assert "date" in ctx


@pytest.mark.django_db
class TestProposalQuerySet:
    def test_with_client(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user, title="Test", client=client_model
        )
        result = Proposal.objects.with_client().get(id=proposal.id)
        assert result.client == client_model

    def test_with_tags(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user, title="Test", client=client_model
        )
        tag = Tag.objects.create(owner=user, name="Python", slug="python")
        proposal.tags.add(tag)

        result = Proposal.objects.with_tags().get(id=proposal.id)
        assert tag in result.tags.all()

    def test_pending_response_filter(self, user, client_model):
        sent = Proposal.objects.create(
            owner=user,
            title="Sent",
            client=client_model,
            status=ProposalStatus.SENT,
        )
        viewed = Proposal.objects.create(
            owner=user,
            title="Viewed",
            client=client_model,
            status=ProposalStatus.VIEWED,
        )
        draft = Proposal.objects.create(
            owner=user,
            title="Draft",
            client=client_model,
            status=ProposalStatus.DRAFT,
        )

        pending = Proposal.objects.pending_response()
        assert sent in pending
        assert viewed in pending
        assert draft not in pending

    def test_accepted_filter(self, user, client_model):
        accepted = Proposal.objects.create(
            owner=user,
            title="Accepted",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
        )
        rejected = Proposal.objects.create(
            owner=user,
            title="Rejected",
            client=client_model,
            status=ProposalStatus.REJECTED,
        )

        result = Proposal.objects.accepted()
        assert accepted in result
        assert rejected not in result


@pytest.mark.django_db
class TestFollowUpModel:
    def test_create_followup(self, user, client_model, accepted_proposal):
        followup = FollowUp.objects.create(
            proposal=accepted_proposal,
            description="Follow up call",
            due_date=date.today() + timedelta(days=3),
        )
        assert followup.completed is False
        assert followup.completed_at is None


@pytest.mark.django_db
class TestTimeEntryQuerySet:
    def test_billable_filter(self, user, client_model, accepted_proposal):
        billable = TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("5.00"),
            billable=True,
        )
        non_billable = TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("3.00"),
            billable=False,
        )

        result = TimeEntry.objects.filter(billable=True)
        assert billable in result
        assert non_billable not in result
