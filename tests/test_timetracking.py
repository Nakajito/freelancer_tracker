from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.timetracking.models import TimeEntry
from apps.timetracking.services import BillableAggregationService


@pytest.mark.django_db
class TestWeeklySummary:
    def test_aggregates_this_week(self, user, accepted_proposal):
        today = date.today()
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=today,
            hours=Decimal("4.00"),
            billable=True,
        )
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=today,
            hours=Decimal("2.00"),
            billable=False,
        )
        s = BillableAggregationService.get_weekly_summary(user)
        assert s["total_hours"] == Decimal("6.00")
        assert s["billable_ratio"] == Decimal("67")

    def test_last_week_separate_bucket(self, user, accepted_proposal):
        last_week = date.today() - timedelta(days=7)
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=last_week,
            hours=Decimal("3.00"),
            billable=True,
        )
        s = BillableAggregationService.get_weekly_summary(user)
        assert s["total_hours"] == Decimal("0")
        assert s["last_week_hours"] == Decimal("3.00")

    def test_zero_when_empty(self, user):
        s = BillableAggregationService.get_weekly_summary(user)
        assert s["total_hours"] == Decimal("0")
        assert s["billable_ratio"] == Decimal("0")
        assert s["last_week_hours"] == Decimal("0")


@pytest.mark.django_db
class TestTimeEntryListView:
    def test_kpis_in_context(self, authed_client, user, accepted_proposal):
        TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("2.00"),
            billable=True,
        )
        response = authed_client.get(reverse("timeentry-list"))
        assert response.status_code == 200
        assert "total_hours" in response.context
        assert "billable_ratio" in response.context
        assert "last_week_hours" in response.context
        assert response.context["total_hours"] == Decimal("2.00")
