from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

from apps.proposals.models import Proposal, ProposalStatus
from apps.timetracking.models import TimeEntry


class FunnelMetrics:
    def __init__(
        self, total: int, sent: int, viewed: int, responded: int, accepted: int
    ):
        self.total = total
        self.sent = sent
        self.viewed = viewed
        self.responded = responded
        self.accepted = accepted
        self.conversion_rate = round((accepted / sent * 100), 2) if sent > 0 else 0


class ConversionMetrics:
    def __init__(self, won: int, lost: int, pending: int):
        self.won = won
        self.lost = lost
        self.pending = pending
        self.win_rate = round((won / (won + lost) * 100), 2) if (won + lost) > 0 else 0


class ForecastMetrics:
    def __init__(self, expected_wins: int, expected_amount: Decimal):
        self.expected_wins = expected_wins
        self.expected_amount = expected_amount


class HourlyRateMetrics:
    def __init__(
        self, total_hours: Decimal, total_amount: Decimal, hourly_rate: Decimal
    ):
        self.total_hours = total_hours
        self.total_amount = total_amount
        self.hourly_rate = hourly_rate


class DashboardService:
    @staticmethod
    def get_funnel_metrics(user, days: int = 30) -> FunnelMetrics:
        cutoff = timezone.now().date() - timedelta(days=days)

        proposals = Proposal.objects.for_user(user).filter(sent_date__gte=cutoff)

        return FunnelMetrics(
            total=proposals.count(),
            sent=proposals.exclude(status=ProposalStatus.DRAFT).count(),
            viewed=proposals.filter(status=ProposalStatus.VIEWED).count(),
            responded=proposals.filter(
                status__in=[ProposalStatus.RESPONDED, ProposalStatus.NEGOTIATING]
            ).count(),
            accepted=proposals.filter(status=ProposalStatus.ACCEPTED).count(),
        )

    @staticmethod
    def get_conversion_metrics(user, days: int = 30) -> ConversionMetrics:
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
