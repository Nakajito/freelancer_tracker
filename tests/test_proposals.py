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


@pytest.mark.django_db
class TestSearchView:
    def test_requires_login(self, client):
        response = client.get(reverse("search"), {"q": "test"})
        assert response.status_code == 302

    def test_empty_query_returns_no_results(self, authed_client):
        response = authed_client.get(reverse("search"), {"q": ""})
        assert response.status_code == 200
        assert response.context["proposals"] == []
        assert response.context["clients"] == []

    def test_short_query_returns_no_results(self, authed_client):
        response = authed_client.get(reverse("search"), {"q": "a"})
        assert response.status_code == 200
        assert response.context["proposals"] == []

    def test_finds_proposal_by_title(self, authed_client, proposal):
        response = authed_client.get(reverse("search"), {"q": "Test Proposal"})
        assert response.status_code == 200
        assert proposal in response.context["proposals"]

    def test_finds_proposal_by_client_name(self, authed_client, proposal, client_model):
        response = authed_client.get(reverse("search"), {"q": client_model.name})
        assert response.status_code == 200
        assert proposal in response.context["proposals"]

    def test_finds_client_by_name(self, authed_client, client_model):
        response = authed_client.get(reverse("search"), {"q": "Test Client"})
        assert response.status_code == 200
        assert client_model in response.context["clients"]

    def test_does_not_return_other_user_results(self, authed_client, other_user):
        other_proposal = Proposal.objects.create(
            owner=other_user,
            title="Secret Proposal",
            status=ProposalStatus.DRAFT,
            amount=500,
        )
        response = authed_client.get(reverse("search"), {"q": "Secret"})
        assert response.status_code == 200
        assert other_proposal not in response.context["proposals"]

    def test_case_insensitive_search(self, authed_client, proposal):
        response = authed_client.get(reverse("search"), {"q": "test proposal"})
        assert response.status_code == 200
        assert proposal in response.context["proposals"]


@pytest.mark.django_db
class TestProposalQuerySetSearch:
    def test_search_by_title(self, user, proposal):
        results = Proposal.objects.for_user(user).search("Test Proposal")
        assert proposal in results

    def test_search_by_client_name(self, user, proposal, client_model):
        results = Proposal.objects.for_user(user).search(client_model.name)
        assert proposal in results

    def test_search_no_match(self, user, proposal):
        results = Proposal.objects.for_user(user).search("xyznonexistent")
        assert proposal not in results


@pytest.mark.django_db
class TestProposalListPeriodFilter:
    def _proposal(self, user, client_model, sent_date=None, **kwargs):
        kwargs.setdefault("status", ProposalStatus.DRAFT)
        return Proposal.objects.create(
            owner=user,
            title=f"P-{sent_date}",
            client=client_model,
            sent_date=sent_date,
            **kwargs,
        )

    def test_year_month_filter_sent_date(self, authed_client, user, client_model):
        self._proposal(user, client_model, sent_date=date(2026, 5, 10))
        self._proposal(user, client_model, sent_date=date(2026, 3, 10))
        url = reverse("proposal-list") + "?year=2026&month=5&date_field=sent_date"
        response = authed_client.get(url)
        assert response.status_code == 200
        assert len(list(response.context["proposals"])) == 1

    def test_year_month_filter_created_at(self, authed_client, user, client_model):
        self._proposal(user, client_model)  # created now, no sent_date
        today = date.today()
        url = (
            reverse("proposal-list")
            + f"?year={today.year}&month={today.month}&date_field=created_at"
        )
        response = authed_client.get(url)
        assert len(list(response.context["proposals"])) >= 1

    def test_sent_date_null_fallback(self, authed_client, user, client_model):
        # proposal with no sent_date → should match via created_at
        p = self._proposal(user, client_model)  # sent_date=None
        today = date.today()
        url = (
            reverse("proposal-list")
            + f"?year={today.year}&month={today.month}&date_field=sent_date"
        )
        response = authed_client.get(url)
        assert p in list(response.context["proposals"])

    def test_no_period_params_returns_all(
        self, authed_client, user, client_model, proposal
    ):
        response = authed_client.get(reverse("proposal-list"))
        assert response.status_code == 200
        assert proposal in list(response.context["proposals"])

    def test_context_has_year_and_month_choices(self, authed_client):
        response = authed_client.get(reverse("proposal-list"))
        ctx = response.context
        assert "year_choices" in ctx
        assert "month_choices" in ctx
        assert len(ctx["month_choices"]) == 12
        assert len(ctx["year_choices"]) == 5

    def test_year_only_filter_sent_date(self, authed_client, user, client_model):
        self._proposal(user, client_model, sent_date=date(2026, 3, 10))
        self._proposal(user, client_model, sent_date=date(2025, 3, 10))
        url = reverse("proposal-list") + "?year=2026&month=&date_field=sent_date"
        response = authed_client.get(url)
        proposals = list(response.context["proposals"])
        assert len(proposals) == 1
        assert proposals[0].sent_date.year == 2026

    def test_month_without_year_defaults_to_current_year(
        self, authed_client, user, client_model
    ):
        today = date.today()
        self._proposal(user, client_model, sent_date=today)
        self._proposal(
            user, client_model, sent_date=date(today.year - 1, today.month, 1)
        )
        url = (
            reverse("proposal-list")
            + f"?year=&month={today.month}&date_field=sent_date"
        )
        response = authed_client.get(url)
        proposals = list(response.context["proposals"])
        years = {p.sent_date.year for p in proposals if p.sent_date}
        assert today.year in years
        assert today.year - 1 not in years

    def test_period_combines_with_status_filter(
        self, authed_client, user, client_model
    ):
        self._proposal(
            user, client_model, sent_date=date(2026, 5, 1), status=ProposalStatus.SENT
        )
        self._proposal(
            user, client_model, sent_date=date(2026, 5, 2), status=ProposalStatus.DRAFT
        )
        url = (
            reverse("proposal-list")
            + "?year=2026&month=5&date_field=sent_date&status=sent"
        )
        response = authed_client.get(url)
        proposals = list(response.context["proposals"])
        assert len(proposals) == 1
        assert proposals[0].status == ProposalStatus.SENT
