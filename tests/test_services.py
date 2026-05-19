import pytest
from decimal import Decimal
from datetime import date, timedelta

from apps.proposals.models import Proposal, ProposalStatus, Platform
from apps.proposals.services import DuplicateCheckService, StatusTransitionService
from apps.followups.models import FollowUp
from apps.followups.services import FollowUpQuerySet, AutoSuggestService
from apps.timetracking.models import TimeEntry, RecurringRetainer
from apps.timetracking.services import (
    BillableAggregationService,
    RetainerGeneratorService,
)
from apps.exports.services import CSVExporter, JSONExporter, MonthlySummaryGenerator


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
    def test_upcoming_followups(self, user, client_model, accepted_proposal):
        followup = FollowUp.objects.create(
            proposal=accepted_proposal,
            description="Follow up",
            due_date=date.today() + timedelta(days=3),
        )
        result = FollowUpQuerySet.upcoming(user)
        assert followup in result

    def test_overdue_followups(self, user, client_model, accepted_proposal):
        followup = FollowUp.objects.create(
            proposal=accepted_proposal,
            description="Overdue",
            due_date=date.today() - timedelta(days=1),
        )
        result = FollowUpQuerySet.overdue(user)
        assert followup in result

    def test_auto_suggest_service(self, user, client_model, accepted_proposal):
        suggestions = AutoSuggestService.suggest_follow_ups(accepted_proposal)
        assert isinstance(suggestions, list)


@pytest.mark.django_db
class TestTimeTrackingServices:
    def test_billable_aggregation_for_proposal(
        self, user, client_model, accepted_proposal
    ):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("5.00"),
            billable=True,
        )
        result = BillableAggregationService.get_total_for_proposal(accepted_proposal)
        assert result.billable_hours == Decimal("5.00")

    def test_weekly_summary(self, user, client_model, accepted_proposal):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("8.00"),
            billable=True,
        )
        summary = BillableAggregationService.get_weekly_summary(user)
        assert "total_hours" in summary
        assert summary["total_hours"] == Decimal("8.00")

    def test_retainer_generator(self, user, client_model):
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
        entries = RetainerGeneratorService.generate_entries(
            retainer, date.today().year, date.today().month
        )
        assert isinstance(entries, list)


@pytest.mark.django_db
class TestExportServices:
    def test_csv_exporter_proposals(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        csv_data = "".join(
            CSVExporter.export_proposals(Proposal.objects.filter(id=proposal.id))
        )
        assert "Test Proposal" in csv_data

    def test_json_exporter_proposals(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        data = JSONExporter.export_proposals(Proposal.objects.filter(id=proposal.id))
        assert len(data) == 1
        assert data[0]["title"] == "Test Proposal"

    def test_monthly_summary_generator(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Test",
            client=client_model,
            sent_date=date.today(),
            status=ProposalStatus.SENT,
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
        assert "period_label" in result
        assert result["proposals_sent"] == 1
