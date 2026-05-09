"""Aggregation and recurring-retainer services for time-entry data."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.timetracking.models import RecurringRetainer, TimeEntry


class BillableAggregation:
    """Container for total/billable hour sums with optional revenue."""

    def __init__(
        self,
        total_hours: Decimal,
        billable_hours: Decimal,
        total_amount: Optional[Decimal] = None,
    ):
        self.total_hours = total_hours
        self.billable_hours = billable_hours
        self.total_amount = total_amount


class BillableAggregationService:
    """Aggregations over ``TimeEntry`` rows for one proposal or one user."""


    @staticmethod
    def get_total_for_proposal(proposal) -> BillableAggregation:
        """Sum hours logged against a single proposal."""
        result = TimeEntry.objects.filter(proposal=proposal).aggregate(
            total=Sum("hours"),
            billable=Sum("hours", filter=models.Q(billable=True)),
        )

        return BillableAggregation(
            total_hours=result["total"] or Decimal("0.00"),
            billable_hours=result["billable"] or Decimal("0.00"),
        )

    @staticmethod
    def get_weekly_summary(user) -> dict:
        """Return current-week totals plus last-week hours for KPI cards.

        Returns:
            ``{"total_hours", "billable_ratio", "last_week_hours"}``.
        """
        today = timezone.now().date()
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)

        this_week = TimeEntry.objects.filter(
            proposal__owner=user,
            date__gte=this_week_start,
            date__lte=today,
        ).aggregate(
            total=Sum("hours"),
            billable=Sum("hours", filter=models.Q(billable=True)),
        )
        last_week = TimeEntry.objects.filter(
            proposal__owner=user,
            date__gte=last_week_start,
            date__lt=this_week_start,
        ).aggregate(total=Sum("hours"))

        total_hours = this_week["total"] or Decimal("0")
        billable_hours = this_week["billable"] or Decimal("0")
        billable_ratio = (
            round((billable_hours / total_hours) * 100, 0)
            if total_hours > 0
            else Decimal("0")
        )

        return {
            "total_hours": total_hours,
            "billable_ratio": billable_ratio,
            "last_week_hours": last_week["total"] or Decimal("0"),
        }

    @staticmethod
    def get_total_for_user(user, start_date=None, end_date=None):
        """Sum hours across all proposals owned by ``user`` in a date window."""
        queryset = TimeEntry.objects.filter(proposal__owner=user)

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        result = queryset.aggregate(
            total=Sum("hours"),
            billable=Sum("hours", filter=models.Q(billable=True)),
        )

        return BillableAggregation(
            total_hours=result["total"] or Decimal("0.00"),
            billable_hours=result["billable"] or Decimal("0.00"),
        )


class RetainerGeneratorService:
    @staticmethod
    def generate_entries(
        retainer: RecurringRetainer, year: int, month: int
    ) -> list[TimeEntry]:
        if not retainer.active:
            return []

        _, last_day = monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)

        existing = TimeEntry.objects.filter(
            proposal=retainer.proposal,
            date__gte=start_date,
            date__lte=end_date,
        ).exists()

        if existing:
            return []

        hours_per_entry = Decimal("1.00")
        num_entries = int(retainer.monthly_hours / hours_per_entry)

        entries = []
        current_date = start_date
        for _ in range(num_entries):
            entry = TimeEntry(
                proposal=retainer.proposal,
                date=current_date,
                hours=hours_per_entry,
                description=f"Recurring retainer - {month}/{year}",
                billable=True,
                override_status_restriction=True,
            )
            entries.append(entry)
            current_date += timedelta(days=1)

        return TimeEntry.objects.bulk_create(entries)
