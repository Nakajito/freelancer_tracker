from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.dashboard.services import DashboardService
from apps.followups.models import FollowUp
from apps.proposals.models import Platform, Proposal, ProposalStatus


@pytest.mark.django_db
class TestFunnelMetrics:
    def test_accepted_amount_sums_only_accepted(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Won",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("1500"),
            sent_date=date.today() - timedelta(days=5),
        )
        Proposal.objects.create(
            owner=user,
            title="Lost",
            client=client_model,
            status=ProposalStatus.REJECTED,
            amount=Decimal("9999"),
            sent_date=date.today() - timedelta(days=5),
        )

        m = DashboardService.get_funnel_metrics(user)
        assert m.accepted == 1
        assert m.accepted_amount == Decimal("1500")

    def test_accepted_amount_zero_when_none(self, user):
        m = DashboardService.get_funnel_metrics(user)
        assert m.accepted_amount == Decimal("0")


@pytest.mark.django_db
class TestUrgentFollowups:
    def test_returns_pending_only(self, user, proposal):
        active = FollowUp.objects.create(
            proposal=proposal,
            description="Pending",
            due_date=date.today() + timedelta(days=1),
        )
        FollowUp.objects.create(
            proposal=proposal,
            description="Done",
            due_date=date.today(),
            completed=True,
        )

        result = DashboardService.get_urgent_followups(user)
        assert active in result
        assert len(result) == 1

    def test_owner_isolation(self, user, other_user, proposal):
        FollowUp.objects.create(
            proposal=proposal,
            description="Mine",
            due_date=date.today(),
        )
        assert DashboardService.get_urgent_followups(other_user) == []

    def test_limit(self, user, proposal):
        for i in range(8):
            FollowUp.objects.create(
                proposal=proposal,
                description=f"f{i}",
                due_date=date.today() + timedelta(days=i),
            )
        assert len(DashboardService.get_urgent_followups(user, limit=3)) == 3

    def test_is_overdue_property(self, user, proposal):
        past = FollowUp.objects.create(
            proposal=proposal,
            description="Past",
            due_date=date.today() - timedelta(days=1),
        )
        future = FollowUp.objects.create(
            proposal=proposal,
            description="Future",
            due_date=date.today() + timedelta(days=1),
        )
        assert past.is_overdue is True
        assert future.is_overdue is False


@pytest.mark.django_db
class TestEarningsChart:
    def test_returns_n_months(self, user):
        chart = DashboardService.get_earnings_chart(user, months=6)
        assert len(chart["labels"]) == 6
        assert len(chart["data"]) == 6

    def test_sums_accepted_by_response_month(self, user, client_model):
        last_month = (date.today().replace(day=1) - timedelta(days=1)).replace(day=15)
        Proposal.objects.create(
            owner=user,
            title="Won last month",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("2500"),
            sent_date=last_month - timedelta(days=10),
            actual_response_date=last_month,
        )
        chart = DashboardService.get_earnings_chart(user, months=3)
        assert sum(chart["data"]) == 2500.0

    def test_falls_back_to_sent_date(self, user, client_model):
        this_month = date.today().replace(day=10)
        Proposal.objects.create(
            owner=user,
            title="No response yet",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("700"),
            sent_date=this_month,
        )
        chart = DashboardService.get_earnings_chart(user, months=2)
        assert chart["data"][-1] == 700.0

    def test_respects_anchor_date(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Old win",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("1200"),
            sent_date=date(2025, 1, 10),
            actual_response_date=date(2025, 1, 15),
        )
        chart = DashboardService.get_earnings_chart(user, months=3, anchor_date=date(2025, 2, 1))
        assert "Jan 2025" in chart["labels"]
        assert sum(chart["data"]) == 1200.0


@pytest.mark.django_db
class TestPlatformConversion:
    def test_rate_per_platform(self, user, client_model):
        today = date.today().replace(day=10)
        for status in [
            ProposalStatus.ACCEPTED,
            ProposalStatus.SENT,
            ProposalStatus.SENT,
        ]:
            Proposal.objects.create(
                owner=user,
                title="P",
                client=client_model,
                platform=Platform.UPWORK,
                status=status,
                sent_date=today,
                amount=Decimal("100"),
            )
        start = date(today.year, today.month, 1)
        end = date(today.year + (1 if today.month == 12 else 0), today.month % 12 + 1, 1)
        rows = DashboardService.get_platform_conversion(user, start, end)
        upwork = next(r for r in rows if r["name"] == "Upwork")
        assert upwork["rate"] == pytest.approx(33.3, abs=0.1)

    def test_skips_empty_platforms(self, user):
        rows = DashboardService.get_platform_conversion(user, date(2026, 1, 1), date(2026, 2, 1))
        assert rows == []


@pytest.mark.django_db
class TestPlatformStats:
    def test_returns_per_platform_row(self, user, client_model):
        today = date.today().replace(day=5)
        Proposal.objects.create(
            owner=user,
            title="P",
            client=client_model,
            platform=Platform.LINKEDIN,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("3000"),
            sent_date=today - timedelta(days=2),
            actual_response_date=today,
        )
        start = date(today.year, today.month, 1)
        end = date(today.year + (1 if today.month == 12 else 0), today.month % 12 + 1, 1)
        rows = DashboardService.get_platform_stats(user, start, end)
        linkedin = next(r for r in rows if r["name"] == "LinkedIn")
        assert linkedin["sent"] == 1
        assert linkedin["success_rate"] == 100.0
        assert linkedin["earned"] == Decimal("3000")
        assert linkedin["avg_response"] == "2.0d"


@pytest.mark.django_db
class TestDashboardView:
    def test_renders_with_full_context(self, authed_client, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Won",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("1000"),
            sent_date=date.today() - timedelta(days=2),
        )
        response = authed_client.get(reverse("dashboard"))
        assert response.status_code == 200
        ctx = response.context
        assert "funnel" in ctx
        assert "conversion" in ctx
        assert "forecast" in ctx
        assert "hourly_rate" in ctx
        assert "urgent_followups" in ctx
        assert ctx["funnel"].accepted == 1


@pytest.mark.django_db
class TestMonthlySummaryView:
    def test_passes_chart_and_stats(self, authed_client, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="P",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal("400"),
            sent_date=date.today().replace(day=10),
        )
        response = authed_client.get(reverse("monthly-summary"))
        assert response.status_code == 200
        ctx = response.context
        assert "chart_labels" in ctx
        assert "chart_data" in ctx
        assert "platform_conversion" in ctx
        assert "platform_stats" in ctx
        assert "hourly_rate" in ctx
        assert ctx["summary"]["period_label"]


@pytest.mark.django_db
class TestMonthlySummaryViewPeriodFilter:
    def _proposal(self, user, client_model, sent_date, amount="500"):
        return Proposal.objects.create(
            owner=user,
            title=f"P-{sent_date}",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal(amount),
            sent_date=sent_date,
        )

    def test_period_year_filters_to_correct_year(self, authed_client, user, client_model):
        self._proposal(user, client_model, date(2025, 6, 1), "1000")
        self._proposal(user, client_model, date(2026, 1, 15), "2000")

        response = authed_client.get(reverse("monthly-summary") + "?period=year&year=2025")
        assert response.status_code == 200
        summary = response.context["summary"]
        assert summary["proposals_sent"] == 1
        assert summary["total_amount"] == Decimal("1000")

    def test_period_30_ignores_year_param(self, authed_client, user, client_model):
        self._proposal(user, client_model, date(2025, 6, 1), "999")
        self._proposal(user, client_model, date.today() - timedelta(days=5), "300")

        response = authed_client.get(reverse("monthly-summary") + "?period=30&year=2025")
        assert response.status_code == 200
        summary = response.context["summary"]
        assert summary["total_amount"] == Decimal("300")

    def test_period_90_ignores_year_param(self, authed_client, user, client_model):
        self._proposal(user, client_model, date(2025, 6, 1), "888")
        self._proposal(user, client_model, date.today() - timedelta(days=15), "400")

        response = authed_client.get(reverse("monthly-summary") + "?period=90&year=2025")
        assert response.status_code == 200
        summary = response.context["summary"]
        assert summary["total_amount"] == Decimal("400")

    def test_default_period_is_90(self, authed_client):
        response = authed_client.get(reverse("monthly-summary"))
        assert response.status_code == 200
        assert response.context["period"] == "90"

    def test_chart_anchor_matches_period_end(self, authed_client, user, client_model):
        # Oct 2025 falls within the 6-month window ending Dec 2025
        self._proposal(user, client_model, date(2025, 10, 15), "750")

        response = authed_client.get(reverse("monthly-summary") + "?period=year&year=2025")
        assert response.status_code == 200
        import json
        chart_labels = json.loads(response.context["chart_labels"])
        chart_data = json.loads(response.context["chart_data"])
        # Last label must be Dec 2025 (anchor = Dec 31 2025), not a 2026 month
        assert chart_labels[-1] == "Dec 2025"
        assert "Oct 2025" in chart_labels
        idx = chart_labels.index("Oct 2025")
        assert chart_data[idx] == 750.0
