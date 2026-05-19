from decimal import Decimal
from datetime import date

import pytest

from apps.proposals.models import Proposal, ProposalStatus, Platform
from apps.exports.services import CSVExporter, JSONExporter


@pytest.mark.django_db
class TestProposalAPIViews:
    def test_duplicate_check_no_duplicate(self, user, client_model):
        from apps.proposals.services import DuplicateCheckService

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
        from apps.proposals.services import DuplicateCheckService

        result = DuplicateCheckService.check_duplicate(
            user, client_model, Platform.UPWORK
        )
        assert result.is_duplicate is True


@pytest.mark.django_db
class TestExportAPIViews:
    def test_csv_export(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        proposals = Proposal.objects.filter(id=proposal.id)
        csv_result = "".join(CSVExporter.export_proposals(proposals))
        assert "Test Proposal" in csv_result

    def test_json_export(self, user, client_model):
        proposal = Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        proposals = Proposal.objects.filter(id=proposal.id)
        data = JSONExporter.export_proposals(proposals)
        assert len(data) == 1
        assert data[0]["title"] == "Test Proposal"


@pytest.mark.django_db
class TestMonthlySummaryAPI:
    def test_monthly_summary_generation(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Test",
            client=client_model,
            sent_date=date.today(),
            status=ProposalStatus.SENT,
        )
        from apps.exports.services import MonthlySummaryGenerator

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
        assert "proposals_sent" in result
