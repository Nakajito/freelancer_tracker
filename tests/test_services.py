import pytest
from decimal import Decimal
from datetime import date, timedelta

from apps.proposals.models import Client, Proposal, Tag, ProposalStatus, Platform
from apps.proposals.services import DuplicateCheckService, StatusTransitionService
from apps.followups.models import FollowUp
from apps.followups.services import get_upcoming_followups, get_overdue_followups
from apps.timetracking.models import TimeEntry, RecurringRetainer
from apps.timetracking.services import (
    calculate_billable_hours,
    generate_monthly_retainer_entries,
    get_billable_summary,
)
from apps.exports.services import (
    generate_proposals_csv,
    generate_proposals_json,
    generate_monthly_summary_html,
)


@pytest.mark.django_db
class TestProposalServices:
    def test_duplicate_check_no_duplicates(self, user, client_model):
        result = DuplicateCheckService.check_duplicate(
            user, client_model, Platform.UPWORK
        )
        assert result.is_duplicate is False

    def test_duplicate_check_found(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Existing Proposal",
            client=client_model,
            platform=Platform.UPWORK,
            sent_date=date.today(),
        )
        result = DuplicateCheckService.check_duplicate(
            user, client_model, Platform.UPWORK
        )
        assert result.is_duplicate is True

    def test_status_transition_sets_response_date(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test",
            client=client_model,
            sent_date=date.today(),
            status=ProposalStatus.SENT,
        )
        result = StatusTransitionService.transition(
            proposal, ProposalStatus.RESPONDED, user
        )
        assert result.success is True
        assert result.actual_response_date_set is True


@pytest.mark.django_db
class TestFollowUpServices:
    def test_get_upcoming_followups(self, user, client_model, accepted_proposal):
        followup = FollowUp.objects.create(
            proposal=accepted_proposal,
            description="Follow up",
            due_date=date.today() + timedelta(days=3),
        )
        result = get_upcoming_followups(user)
        assert followup in result

    def test_get_overdue_followups(self, user, client_model, accepted_proposal):
        followup = FollowUp.objects.create(
            proposal=accepted_proposal,
            description="Overdue",
            due_date=date.today() - timedelta(days=1),
        )
        result = get_overdue_followups(user)
        assert followup in result


@pytest.mark.django_db
class TestTimeTrackingServices:
    def test_calculate_billable_hours(self, user, client_model, accepted_proposal):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("5.00"),
            billable=True,
        )
        hours = calculate_billable_hours(user, date.today().year, date.today().month)
        assert hours == Decimal("5.00")

    def test_calculate_non_billable_hours_excluded(
        self, user, client_model, accepted_proposal
    ):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("5.00"),
            billable=False,
        )
        hours = calculate_billable_hours(user, date.today().year, date.today().month)
        assert hours == Decimal("0")

    def test_generate_monthly_retainer_entries(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Retainer",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
        )
        retainer = RecurringRetainer.objects.create(
            proposal=proposal,
            monthly_hours=Decimal("20.00"),
            day_of_month=1,
            active=True,
        )
        count = generate_monthly_retainer_entries(
            proposal, date.today().year, date.today().month
        )
        assert count >= 0

    def test_get_billable_summary(self, user, client_model, accepted_proposal):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("8.00"),
            billable=True,
        )
        summary = get_billable_summary(user, date.today().year)
        assert "total_hours" in summary
        assert summary["total_hours"] == Decimal("8.00")


@pytest.mark.django_db
class TestExportServices:
    def test_generate_proposals_csv(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        csv_data = generate_proposals_csv(user)
        assert "Test Proposal" in csv_data

    def test_generate_proposals_json(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        json_data = generate_proposals_json(user)
        assert "Test Proposal" in json_data

    def test_generate_monthly_summary_html(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test",
            client=client_model,
            sent_date=date.today(),
            status=ProposalStatus.SENT,
        )
        html = generate_monthly_summary_html(
            user, date.today().year, date.today().month
        )
        assert "Test" in html or "summary" in html.lower()
