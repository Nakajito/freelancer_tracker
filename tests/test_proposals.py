import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse

from apps.proposals.forms import ProposalForm
from apps.proposals.models import Client, Platform, Proposal, Tag, ProposalStatus


@pytest.mark.django_db
class TestClientModel:
    def test_create_client(self, user):
        client = Client.objects.create(owner=user, name="Test Company")
        assert client.name == "Test Company"
        assert client.owner == user

    def test_client_unique_constraint(self, user, client_model):
        with pytest.raises(Exception):
            Client.objects.create(owner=user, name=client_model.name)

    def test_client_str(self, client_model):
        assert str(client_model) == client_model.name


@pytest.mark.django_db
class TestTagModel:
    def test_create_tag(self, user):
        tag = Tag.objects.create(owner=user, name="Django", slug="django")
        assert tag.name == "Django"
        assert tag.slug == "django"


@pytest.mark.django_db
class TestProposalModel:
    def test_create_proposal(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1500.00"),
            status=ProposalStatus.DRAFT,
        )
        assert proposal.title == "Test Proposal"
        assert proposal.amount == Decimal("1500.00")

    def test_proposal_response_time_none_when_no_dates(self, proposal):
        assert proposal.response_time is None

    def test_proposal_response_time_calculated(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test",
            client=client_model,
            sent_date=date(2024, 1, 1),
            actual_response_date=date(2024, 1, 5),
        )
        assert proposal.response_time == 4


@pytest.mark.django_db
class TestProposalQuerySet:
    def test_for_user_filter(self, user, other_user, proposal, db):
        user_proposals = Proposal.objects.for_user(user)
        assert proposal in user_proposals

    def test_pending_response(self, user, client_model):
        sent = Proposal.objects.create(
            owner=user, title="Sent", client=client_model, status=ProposalStatus.SENT
        )
        draft = Proposal.objects.create(
            owner=user, title="Draft", client=client_model, status=ProposalStatus.DRAFT
        )
        pending = Proposal.objects.pending_response()
        assert sent in pending
        assert draft not in pending

    def test_accepted_filter(self, user, client_model, accepted_proposal):
        accepted = Proposal.objects.accepted()
        assert accepted_proposal in accepted


@pytest.mark.django_db
class TestProposalForm:
    def test_filters_clients_and_tags_by_user(self, user, other_user, client_model):
        other_client = Client.objects.create(owner=other_user, name="Other Client")
        own_tag = Tag.objects.create(owner=user, name="Django", slug="django")
        other_tag = Tag.objects.create(owner=other_user, name="React", slug="react")

        form = ProposalForm(user=user)

        assert client_model in form.fields["client"].queryset
        assert other_client not in form.fields["client"].queryset
        assert own_tag in form.fields["tags"].queryset
        assert other_tag not in form.fields["tags"].queryset

    def test_creates_new_client_when_no_existing_client_selected(self, user):
        form = ProposalForm(
            user=user,
            data={
                "title": "New Proposal",
                "platform": Platform.UPWORK,
                "client": "",
                "new_client_name": "Acme",
                "new_client_email": "hello@acme.test",
                "amount": "500.00",
                "status": ProposalStatus.DRAFT,
                "proposal_text": "",
                "sent_date": "",
                "expected_response_date": "",
                "job_url": "",
                "proposal_url": "",
                "tags": [],
            },
        )

        assert form.is_valid(), form.errors
        proposal = form.save(commit=False)
        proposal.owner = user
        proposal = form.save()

        assert proposal.client.name == "Acme"
        assert proposal.client.owner == user

    def test_existing_client_takes_precedence_over_new_client_fields(
        self, user, client_model
    ):
        form = ProposalForm(
            user=user,
            data={
                "title": "New Proposal",
                "platform": Platform.UPWORK,
                "client": client_model.pk,
                "new_client_name": "Ignored Client",
                "new_client_email": "ignored@example.com",
                "amount": "500.00",
                "status": ProposalStatus.DRAFT,
                "proposal_text": "",
                "sent_date": "",
                "expected_response_date": "",
                "job_url": "",
                "proposal_url": "",
                "tags": [],
            },
        )

        assert form.is_valid(), form.errors
        proposal = form.save(commit=False)
        proposal.owner = user
        proposal = form.save()

        assert proposal.client == client_model
        assert not Client.objects.filter(owner=user, name="Ignored Client").exists()


@pytest.mark.django_db
class TestProposalListTemplateChoices:
    def test_filters_use_model_choices(self, authed_client):
        response = authed_client.get(reverse("proposal-list"))

        assert response.status_code == 200
        assert response.context["status_choices"] == list(ProposalStatus.choices)
        assert response.context["platform_choices"] == list(Platform.choices)
