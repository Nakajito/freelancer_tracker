"""Follow-up suggestion engine and queryset filters."""

from __future__ import annotations

from datetime import timedelta
from typing import List

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.followups.models import FollowUp
from apps.proposals.models import Proposal, ProposalStatus


class FollowUpSuggestion:
    """A suggested follow-up date with the reason it was generated."""

    def __init__(self, proposal: Proposal, suggested_date, reason: str):
        self.proposal = proposal
        self.suggested_date = suggested_date
        self.reason = reason


class AutoSuggestService:
    """Heuristics that propose follow-up dates for in-flight proposals."""

    @staticmethod
    def suggest_follow_ups(proposal: Proposal) -> List[FollowUpSuggestion]:
        """Return suggested follow-up dates for a single proposal."""
        suggestions = []

        if proposal.status in [ProposalStatus.SENT, ProposalStatus.VIEWED]:
            if proposal.sent_date:
                suggestions.append(
                    FollowUpSuggestion(
                        proposal=proposal,
                        suggested_date=proposal.sent_date + timedelta(days=3),
                        reason="Follow up 3 days after sending proposal",
                    )
                )

        if proposal.expected_response_date:
            overdue = proposal.expected_response_date < timezone.now().date()
            suggestions.append(
                FollowUpSuggestion(
                    proposal=proposal,
                    suggested_date=proposal.expected_response_date,
                    reason="Check on expected response date"
                    if not overdue
                    else "Expected response date has passed",
                )
            )

        return suggestions


class FollowUpQuerySet:
    """Static helpers that return common follow-up querysets."""

    @staticmethod
    def overdue(user):
        """Pending follow-ups whose ``due_date`` is in the past."""
        return (
            FollowUp.objects.filter(
                proposal__owner=user,
                completed=False,
                due_date__lt=timezone.now().date(),
            )
            .select_related("proposal", "proposal__client")
            .order_by("due_date")
        )

    @staticmethod
    def upcoming(user, days: int = 7):
        """Pending follow-ups due within the next ``days`` days."""
        cutoff = timezone.now().date() + timedelta(days=days)
        return (
            FollowUp.objects.filter(
                proposal__owner=user,
                completed=False,
                due_date__lte=cutoff,
            )
            .select_related("proposal", "proposal__client")
            .order_by("due_date")
        )


class FollowUpScheduler:
    """Creates follow-up entries tied to proposal lifecycle events."""

    @staticmethod
    def schedule_for_expected_response(proposal: Proposal) -> "FollowUp | None":
        """Create a FollowUp with due_date = proposal.expected_response_date.

        Returns None if expected_response_date is falsy.
        """
        if not proposal.expected_response_date:
            return None
        return FollowUp.objects.create(
            proposal=proposal,
            due_date=proposal.expected_response_date,
            description=_("Check on expected response date"),
        )
