import csv
import json
from datetime import date
from io import StringIO
from typing import Iterator

from django.http import HttpResponse


class CSVExporter:
    @staticmethod
    def export_proposals(proposals) -> Iterator[str]:
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
                    p.client.name,
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
    @staticmethod
    def export_proposals(proposals) -> list[dict]:
        return [
            {
                "id": p.id,
                "title": p.title,
                "client": p.client.name,
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
    @staticmethod
    def generate(user, year: int, month: int) -> dict:
        from datetime import date
        from decimal import Decimal

        from django.db.models import Sum

        from apps.proposals.models import Proposal, ProposalStatus
        from apps.timetracking.models import TimeEntry

        start_date = date(year, month, 1)

        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        proposals = Proposal.objects.for_user(user).filter(
            sent_date__gte=start_date,
            sent_date__lt=end_date,
        )

        time_entries = TimeEntry.objects.filter(
            proposal__owner=user,
            date__gte=start_date,
            date__lt=end_date,
        )

        total_hours = time_entries.aggregate(total=Sum("hours"))["total"] or Decimal(
            "0"
        )
        billable_hours = time_entries.filter(billable=True).aggregate(
            total=Sum("hours")
        )["total"] or Decimal("0")

        return {
            "year": year,
            "month": month,
            "proposals_sent": proposals.exclude(status=ProposalStatus.DRAFT).count(),
            "proposals_accepted": proposals.filter(
                status=ProposalStatus.ACCEPTED
            ).count(),
            "proposals_rejected": proposals.filter(
                status=ProposalStatus.REJECTED
            ).count(),
            "total_amount": proposals.aggregate(total=Sum("amount"))["total"]
            or Decimal("0"),
            "total_hours": total_hours,
            "billable_hours": billable_hours,
        }
