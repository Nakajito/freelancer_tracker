"""Read-only metric services that power the main dashboard and analytics."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.followups.models import FollowUp
from apps.proposals.models import Platform, Proposal, ProposalStatus
from apps.timetracking.models import TimeEntry


class FunnelMetrics:
    """Per-status counts for the proposal funnel plus accepted revenue."""

    def __init__(
        self,
        total: int,
        sent: int,
        viewed: int,
        responded: int,
        accepted: int,
        accepted_amount: Decimal,
        status_counts: list[dict] | None = None,
    ):
        self.total = total
        self.sent = sent
        self.viewed = viewed
        self.responded = responded
        self.accepted = accepted
        self.accepted_amount = accepted_amount
        self.status_counts = status_counts or []
        self.conversion_rate = round((accepted / sent * 100), 2) if sent > 0 else 0


class ConversionMetrics:
    """Won / lost / pending counts and win-rate over a period."""

    def __init__(self, won: int, lost: int, pending: int):
        self.won = won
        self.lost = lost
        self.pending = pending
        self.win_rate = round((won / (won + lost) * 100), 2) if (won + lost) > 0 else 0


class ForecastMetrics:
    """Expected wins (count) and value derived from in-flight proposals."""

    def __init__(self, expected_wins: int, expected_amount: Decimal):
        self.expected_wins = expected_wins
        self.expected_amount = expected_amount


class HourlyRateMetrics:
    """Effective hourly rate computed from billable hours and accepted revenue."""

    def __init__(
        self, total_hours: Decimal, total_amount: Decimal, hourly_rate: Decimal
    ):
        self.total_hours = total_hours
        self.total_amount = total_amount
        self.hourly_rate = hourly_rate


class DashboardService:
    """Stateless aggregator that produces dashboard and analytics metrics."""

    @staticmethod
    def get_funnel_metrics(user, days: int = 30) -> FunnelMetrics:
        """Return funnel counts and accepted revenue for the last ``days`` days."""
        cutoff = timezone.now().date() - timedelta(days=days)

        proposals = Proposal.objects.for_user(user).filter(sent_date__gte=cutoff)
        accepted_qs = proposals.filter(status=ProposalStatus.ACCEPTED)
        accepted_amount = accepted_qs.aggregate(total=models.Sum("amount"))[
            "total"
        ] or Decimal("0")
        status_counts = []
        baseline = proposals.count()
        for value, label in ProposalStatus.choices:
            count = proposals.filter(status=value).count()
            status_counts.append(
                {
                    "value": value,
                    "label": label,
                    "count": count,
                    "percentage": round((count / baseline) * 100, 2) if baseline else 0,
                }
            )

        return FunnelMetrics(
            total=baseline,
            sent=proposals.exclude(status=ProposalStatus.DRAFT).count(),
            viewed=proposals.filter(status=ProposalStatus.VIEWED).count(),
            responded=proposals.filter(
                status__in=[ProposalStatus.RESPONDED, ProposalStatus.NEGOTIATING]
            ).count(),
            accepted=accepted_qs.count(),
            accepted_amount=accepted_amount,
            status_counts=status_counts,
        )

    @staticmethod
    def get_conversion_metrics(user, days: int = 30) -> ConversionMetrics:
        """Return won/lost/pending counts plus win-rate over the period."""
        cutoff = timezone.now().date() - timedelta(days=days)

        proposals = Proposal.objects.for_user(user).filter(sent_date__gte=cutoff)

        return ConversionMetrics(
            won=proposals.filter(status=ProposalStatus.ACCEPTED).count(),
            lost=proposals.filter(status=ProposalStatus.REJECTED).count(),
            pending=proposals.filter(
                status__in=[
                    ProposalStatus.SENT,
                    ProposalStatus.VIEWED,
                    ProposalStatus.RESPONDED,
                    ProposalStatus.NEGOTIATING,
                ]
            ).count(),
        )

    @staticmethod
    def get_forecast_metrics(user, days: int = 90) -> ForecastMetrics:
        """Project wins and revenue from in-flight proposals using historical win-rate."""
        cutoff = timezone.now().date() - timedelta(days=days)

        proposals = Proposal.objects.for_user(user).filter(sent_date__gte=cutoff)

        responded = proposals.filter(
            status__in=[ProposalStatus.RESPONDED, ProposalStatus.NEGOTIATING]
        )

        historical = Proposal.objects.for_user(user).filter(
            status=ProposalStatus.ACCEPTED,
            sent_date__gte=cutoff,
        )

        win_rate = (
            historical.count() / proposals.exclude(status=ProposalStatus.DRAFT).count()
            if proposals.exclude(status=ProposalStatus.DRAFT).count() > 0
            else 0
        )

        expected_wins = int(responded.count() * win_rate)
        expected_amount = responded.aggregate(total=models.Sum("amount"))[
            "total"
        ] or Decimal("0")

        return ForecastMetrics(
            expected_wins=expected_wins,
            expected_amount=expected_amount * Decimal(str(win_rate)),
        )

    @staticmethod
    def get_hourly_rate_metrics(user, days: int = 30) -> HourlyRateMetrics:
        """Compute effective hourly rate from accepted revenue / billable hours."""
        cutoff = timezone.now().date() - timedelta(days=days)

        time_entries = TimeEntry.objects.filter(
            proposal__owner=user,
            date__gte=cutoff,
            billable=True,
        )

        total_hours = time_entries.aggregate(total=models.Sum("hours"))[
            "total"
        ] or Decimal("0")

        accepted_proposals = Proposal.objects.for_user(user).filter(
            status=ProposalStatus.ACCEPTED,
        )

        total_amount = accepted_proposals.aggregate(total=models.Sum("amount"))[
            "total"
        ] or Decimal("0")

        hourly_rate = total_amount / total_hours if total_hours > 0 else Decimal("0")

        return HourlyRateMetrics(
            total_hours=total_hours,
            total_amount=total_amount,
            hourly_rate=hourly_rate,
        )

    @staticmethod
    def get_urgent_followups(user, limit: int = 5):
        """Return up to ``limit`` pending follow-ups ordered by ``due_date``."""
        return list(
            FollowUp.objects.filter(
                proposal__owner=user,
                completed=False,
            )
            .select_related("proposal", "proposal__client")
            .order_by("due_date")[:limit]
        )

    @staticmethod
    def get_earnings_chart(
        user, months: int = 6, anchor_date: date | None = None
    ) -> dict:
        """Return labels/data arrays of accepted revenue per month for charting.

        Args:
            user: Authenticated user whose proposals are aggregated.
            months: Number of trailing months to include (anchor month last).
            anchor_date: Last date of the chart window. Defaults to today.

        Returns:
            ``{"labels": [...], "data": [...]}`` ready for Chart.js.
        """
        anchor = anchor_date or timezone.now().date()
        labels: list[str] = []
        data: list[float] = []

        first_of_current = date(anchor.year, anchor.month, 1)
        cursor = first_of_current
        for _ in range(months - 1):
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        bucket_start = cursor

        for _ in range(months):
            _, last_day = monthrange(bucket_start.year, bucket_start.month)
            bucket_end = date(bucket_start.year, bucket_start.month, last_day)

            qs = Proposal.objects.for_user(user).filter(
                status=ProposalStatus.ACCEPTED,
            )
            qs_with_response = qs.filter(
                actual_response_date__gte=bucket_start,
                actual_response_date__lte=bucket_end,
            )
            qs_without_response = qs.filter(
                actual_response_date__isnull=True,
                sent_date__gte=bucket_start,
                sent_date__lte=bucket_end,
            )
            total = (
                qs_with_response.aggregate(total=models.Sum("amount"))["total"]
                or Decimal("0")
            ) + (
                qs_without_response.aggregate(total=models.Sum("amount"))["total"]
                or Decimal("0")
            )

            labels.append(bucket_start.strftime("%b %Y"))
            data.append(float(total))

            next_month = bucket_start.month + 1
            next_year = bucket_start.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            bucket_start = date(next_year, next_month, 1)

        return {"labels": labels, "data": data}

    @staticmethod
    def get_platform_conversion(user, start_date, end_date) -> list[dict]:
        """Return per-platform win-rate dicts for the given date range."""
        start, end = start_date, end_date

        rows: list[dict] = []
        for value, label in Platform.choices:
            sent_qs = (
                Proposal.objects.for_user(user)
                .filter(platform=value)
                .exclude(status=ProposalStatus.DRAFT)
                .filter(
                    Q(sent_date__gte=start, sent_date__lt=end)
                    | Q(
                        sent_date__isnull=True,
                        created_at__date__gte=start,
                        created_at__date__lt=end,
                    )
                )
            )
            sent_count = sent_qs.count()
            if sent_count == 0:
                continue
            accepted_count = sent_qs.filter(status=ProposalStatus.ACCEPTED).count()
            rate = round((accepted_count / sent_count) * 100, 1)
            rows.append({"name": label, "rate": rate})

        rows.sort(key=lambda r: r["rate"], reverse=True)
        return rows

    @staticmethod
    def get_platform_stats(user, start_date, end_date) -> list[dict]:
        """Return per-platform statistics rows for the analytics table."""
        start, end = start_date, end_date

        rows: list[dict] = []
        for value, label in Platform.choices:
            sent_qs = (
                Proposal.objects.for_user(user)
                .filter(platform=value)
                .exclude(status=ProposalStatus.DRAFT)
                .filter(
                    Q(sent_date__gte=start, sent_date__lt=end)
                    | Q(
                        sent_date__isnull=True,
                        created_at__date__gte=start,
                        created_at__date__lt=end,
                    )
                )
            )
            sent_count = sent_qs.count()
            if sent_count == 0:
                continue
            accepted_qs = sent_qs.filter(status=ProposalStatus.ACCEPTED)
            accepted_count = accepted_qs.count()
            success_rate = round((accepted_count / sent_count) * 100, 1)
            earned = accepted_qs.aggregate(total=models.Sum("amount"))[
                "total"
            ] or Decimal("0")

            responded = sent_qs.filter(
                sent_date__isnull=False,
                actual_response_date__isnull=False,
            )
            response_days = [
                (p.actual_response_date - p.sent_date).days for p in responded
            ]
            avg_response = (
                round(sum(response_days) / len(response_days), 1)
                if response_days
                else None
            )

            rows.append(
                {
                    "name": label,
                    "sent": sent_count,
                    "success_rate": success_rate,
                    "earned": earned,
                    "avg_response": f"{avg_response}d"
                    if avg_response is not None
                    else "—",
                }
            )

        rows.sort(key=lambda r: r["sent"], reverse=True)
        return rows
