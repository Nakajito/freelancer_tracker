"""Export services: CSV/JSON proposal exports and monthly HTML summaries."""

import csv
from decimal import Decimal
from io import StringIO
from typing import Iterator

from django.db.models import Q, Sum

from apps.proposals.models import Proposal, ProposalStatus
from apps.timetracking.models import TimeEntry


class CSVExporter:
    """Stream proposals or time entries as CSV rows."""

    @staticmethod
    def export_proposals(proposals) -> Iterator[str]:
        """Yield a single CSV blob for the given ``Proposal`` queryset."""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "ID",
                "Title",
                "Client",
                "Platform",
                "Status",
                "Amount",
                "Sent Date",
                "Expected Response",
                "Actual Response",
                "Paid",
            ]
        )

        for p in proposals:
            writer.writerow(
                [
                    p.id,
                    p.title,
                    p.client.name if p.client else "",
                    p.get_platform_display(),
                    p.get_status_display(),
                    str(p.amount),
                    p.sent_date or "",
                    p.expected_response_date or "",
                    p.actual_response_date or "",
                    "Yes" if p.paid else "No",
                ]
            )

        yield output.getvalue()

    @staticmethod
    def export_time_entries(entries) -> Iterator[str]:
        """Yield a single CSV blob for the given ``TimeEntry`` queryset."""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["ID", "Date", "Proposal", "Hours", "Description", "Billable"])

        for e in entries:
            writer.writerow(
                [
                    e.id,
                    e.date,
                    e.proposal.title,
                    str(e.hours),
                    e.description,
                    "Yes" if e.billable else "No",
                ]
            )

        yield output.getvalue()


class JSONExporter:
    """Serialize proposals to JSON-friendly dicts."""

    @staticmethod
    def export_proposals(proposals) -> list[dict]:
        """Return a list of dicts representing the given proposals."""
        return [
            {
                "id": p.id,
                "title": p.title,
                "client": p.client.name if p.client else "",
                "platform": p.platform,
                "status": p.status,
                "amount": str(p.amount),
                "sent_date": str(p.sent_date) if p.sent_date else None,
                "expected_response_date": str(p.expected_response_date)
                if p.expected_response_date
                else None,
                "actual_response_date": str(p.actual_response_date)
                if p.actual_response_date
                else None,
                "paid": p.paid,
                "tags": [t.name for t in p.tags.all()],
            }
            for p in proposals
        ]


class MonthlySummaryGenerator:
    """Aggregate a user's proposal and time-entry activity for a date range."""

    @staticmethod
    def generate(user, start_date, end_date, period_label: str) -> dict:
        proposals = Proposal.objects.for_user(user).exclude(
            status=ProposalStatus.DRAFT
        ).filter(
            Q(sent_date__gte=start_date, sent_date__lt=end_date)
            | Q(sent_date__isnull=True, created_at__date__gte=start_date, created_at__date__lt=end_date)
        )
        time_entries = TimeEntry.objects.filter(
            proposal__owner=user,
            date__gte=start_date,
            date__lt=end_date,
        )

        total_hours = time_entries.aggregate(total=Sum("hours"))["total"] or Decimal("0")
        billable_hours = time_entries.filter(billable=True).aggregate(
            total=Sum("hours")
        )["total"] or Decimal("0")

        proposals_sent = proposals.count()
        proposals_accepted = proposals.filter(status=ProposalStatus.ACCEPTED).count()
        proposals_rejected = proposals.filter(status=ProposalStatus.REJECTED).count()
        win_rate = (
            round((proposals_accepted / proposals_sent) * 100, 1)
            if proposals_sent > 0
            else 0
        )

        return {
            "period_label": period_label,
            "proposals_sent": proposals_sent,
            "proposals_accepted": proposals_accepted,
            "proposals_rejected": proposals_rejected,
            "win_rate": win_rate,
            "total_amount": proposals.filter(status=ProposalStatus.ACCEPTED).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0"),
            "total_hours": total_hours,
            "billable_hours": billable_hours,
        }
