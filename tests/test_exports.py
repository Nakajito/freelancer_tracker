from datetime import date
from decimal import Decimal

import pytest

from apps.exports.services import MonthlySummaryGenerator
from apps.proposals.models import Proposal, ProposalStatus

JAN_START = date(2026, 1, 1)
JAN_END = date(2026, 2, 1)


@pytest.mark.django_db
class TestMonthlySummaryGenerator:
    def test_period_label(self, user):
        result = MonthlySummaryGenerator.generate(user, JAN_START, JAN_END, "Jan 2026")
        assert result["period_label"] == "Jan 2026"

    def test_win_rate(self, user, client_model):
        target = date(2026, 1, 15)
        Proposal.objects.create(
            owner=user,
            title="Won",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("1000"),
            sent_date=target,
        )
        Proposal.objects.create(
            owner=user,
            title="Lost",
            client=client_model,
            status=ProposalStatus.REJECTED,
            sent_date=target,
        )
        Proposal.objects.create(
            owner=user,
            title="Pending",
            client=client_model,
            status=ProposalStatus.SENT,
            sent_date=target,
        )
        result = MonthlySummaryGenerator.generate(user, JAN_START, JAN_END, "Jan 2026")
        assert result["proposals_sent"] == 3
        assert result["proposals_accepted"] == 1
        assert result["win_rate"] == pytest.approx(33.3, abs=0.1)

    def test_win_rate_zero_when_no_sent(self, user):
        result = MonthlySummaryGenerator.generate(user, JAN_START, JAN_END, "Jan 2026")
        assert result["win_rate"] == 0

    def test_total_amount_from_accepted_only(self, user, client_model):
        target = date(2026, 1, 10)
        Proposal.objects.create(
            owner=user,
            title="Won",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("1500"),
            sent_date=target,
        )
        Proposal.objects.create(
            owner=user,
            title="Pending",
            client=client_model,
            status=ProposalStatus.SENT,
            amount=Decimal("9999"),
            sent_date=target,
        )
        result = MonthlySummaryGenerator.generate(user, JAN_START, JAN_END, "Jan 2026")
        assert result["total_amount"] == Decimal("1500")
