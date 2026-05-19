from decimal import Decimal
from datetime import date, timedelta

import pytest

from apps.proposals.models import Client, Proposal, ProposalStatus, Platform, Tag
from apps.proposals.services import DuplicateCheckService
from apps.exports.services import MonthlySummaryGenerator, JSONExporter
from apps.timetracking.models import TimeEntry, RecurringRetainer
from apps.timetracking.services import BillableAggregationService


@pytest.mark.django_db
class TestDuplicateCheckAPI:
    def test_duplicate_check_service(self, user, client_model):
        result = DuplicateCheckService.check_duplicate(
            user, client_model, Platform.UPWORK
        )
        assert result.is_duplicate is False

    def test_duplicate_check_found(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Existing",
            client=client_model,
            platform=Platform.UPWORK,
            sent_date=date.today(),
        )
        result = DuplicateCheckService.check_duplicate(
            user, client_model, Platform.UPWORK
        )
        assert result.is_duplicate is True
        assert len(result.existing_proposals) > 0


@pytest.mark.django_db
class TestClientModel:
    def test_create_with_email(self, user):
        client = Client.objects.create(
            owner=user, name="Test Corp", email="contact@testcorp.com"
        )
        assert client.email == "contact@testcorp.com"

    def test_create_with_notes(self, user):
        client = Client.objects.create(
            owner=user, name="Test Corp", notes="Important client"
        )
        assert client.notes == "Important client"


@pytest.mark.django_db
class TestTagModel:
    def test_create_tag(self, user):
        tag = Tag.objects.create(owner=user, name="Django", slug="django")
        assert tag.slug == "django"

    def test_tag_unique_constraint(self, user):
        Tag.objects.create(owner=user, name="Python", slug="python")
        with pytest.raises(Exception):
            Tag.objects.create(owner=user, name="Python", slug="python")


@pytest.mark.django_db
class TestProposalModel:
    def test_create_with_all_fields(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Full Proposal",
            client=client_model,
            platform=Platform.UPWORK,
            proposal_text="My proposal text",
            amount=Decimal("1500.00"),
            status=ProposalStatus.DRAFT,
            expected_response_date=date.today() + timedelta(days=7),
            job_url="https://example.com/job",
            proposal_url="https://example.com/proposal",
            paid=True,
        )
        assert proposal.paid is True
        assert proposal.amount == Decimal("1500.00")

    def test_proposal_response_time_with_both_dates(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test",
            client=client_model,
            sent_date=date(2024, 1, 1),
            actual_response_date=date(2024, 1, 10),
        )
        assert proposal.response_time == 9


@pytest.mark.django_db
class TestRecurringRetainer:
    def test_create_retainer(self, user, client_model, accepted_proposal):
        retainer = RecurringRetainer.objects.create(
            proposal=accepted_proposal,
            monthly_hours=Decimal("40.00"),
            day_of_month=1,
            active=True,
        )
        assert retainer.monthly_hours == Decimal("40.00")
        assert retainer.active is True

    def test_create_inactive_retainer(self, user, client_model, accepted_proposal):
        retainer = RecurringRetainer.objects.create(
            proposal=accepted_proposal,
            monthly_hours=Decimal("20.00"),
            day_of_month=15,
            active=False,
        )
        assert retainer.active is False


@pytest.mark.django_db
class TestTimeEntryModel:
    def test_create_with_override(self, user, client_model, accepted_proposal):
        entry = TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("2.00"),
            description="Quick fix",
            override_status_restriction=True,
        )
        assert entry.override_status_restriction is True

    def test_create_non_billable(self, user, client_model, accepted_proposal):
        entry = TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("1.00"),
            billable=False,
        )
        assert entry.billable is False


@pytest.mark.django_db
class TestBillableAggregationService:
    def test_get_total_for_user(self, user, client_model, accepted_proposal):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("8.00"),
            billable=True,
        )
        result = BillableAggregationService.get_total_for_user(user)
        assert result.total_hours == Decimal("8.00")
        assert result.billable_hours == Decimal("8.00")

    def test_get_total_for_user_date_range(self, user, client_model, accepted_proposal):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("8.00"),
            billable=True,
        )
        result = BillableAggregationService.get_total_for_user(
            user, start_date=date.today(), end_date=date.today()
        )
        assert result.total_hours == Decimal("8.00")


@pytest.mark.django_db
class TestJSONExporter:
    def test_export_proposals(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Tagged Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )

        data = JSONExporter.export_proposals(Proposal.objects.filter(id=proposal.id))
        assert len(data) == 1
        assert data[0]["title"] == "Tagged Proposal"


@pytest.mark.django_db
class TestMonthlySummaryGenerator:
    def test_monthly_with_time_entries(self, user, client_model, accepted_proposal):
        Proposal.objects.create(
            owner=user,
            title="Test",
            client=client_model,
            sent_date=date.today(),
            status=ProposalStatus.SENT,
        )
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("8.00"),
            billable=True,
        )
        today = date.today()
        start = today.replace(day=1)
        end = (
            start.replace(
                month=start.month % 12 + 1,
                year=start.year + (1 if start.month == 12 else 0),
            )
        ).replace(day=1)
        result = MonthlySummaryGenerator.generate(
            user, start, end, today.strftime("%b %Y")
        )
        assert result["total_hours"] == Decimal("8.00")
        assert result["billable_hours"] == Decimal("8.00")
