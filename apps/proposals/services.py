"""Proposal business-logic services: duplicate detection and status transitions."""

from datetime import timedelta

from django.utils import timezone
from pydantic import BaseModel

from apps.proposals.models import Proposal, ProposalStatus


class DuplicateCheckResult(BaseModel):
    """Outcome of a duplicate-proposal check."""

    is_duplicate: bool
    existing_proposals: list = []


class StatusTransitionResult(BaseModel):
    """Outcome of a proposal status transition."""

    success: bool
    old_status: str
    new_status: str
    actual_response_date_set: bool = False


class DuplicateCheckService:
    """Detects whether a near-identical proposal was recently submitted."""

    @staticmethod
    def check_duplicate(
        owner,
        client,
        platform: str,
        days: int = 30,
    ) -> DuplicateCheckResult:
        """Check for proposals sent to the same client on the same platform recently.

        Args:
            owner: User who owns the proposals being checked.
            client: Client instance to match against.
            platform: Platform value (e.g. ``Platform.UPWORK``) to match.
            days: Look-back window in days. Defaults to 30.

        Returns:
            DuplicateCheckResult with ``is_duplicate=True`` and matching proposal
            ids/titles/dates when a duplicate exists; ``is_duplicate=False`` otherwise.
        """
        cutoff = timezone.now().date() - timedelta(days=days)

        existing = (
            Proposal.objects.for_user(owner)
            .with_client()
            .filter(
                client=client,
                platform=platform,
                sent_date__gte=cutoff,
            )
        )

        if existing.exists():
            return DuplicateCheckResult(
                is_duplicate=True,
                existing_proposals=list(existing.values("id", "title", "sent_date")),
            )

        return DuplicateCheckResult(is_duplicate=False)


class StatusTransitionService:
    """Applies validated status transitions to proposals and records response dates."""

    RESPONSE_STATUSES = {
        ProposalStatus.RESPONDED,
        ProposalStatus.NEGOTIATING,
        ProposalStatus.ACCEPTED,
        ProposalStatus.REJECTED,
    }

    @staticmethod
    def transition(
        proposal: Proposal, new_status: str, actor
    ) -> StatusTransitionResult:
        """Move a proposal to a new status, auto-setting ``actual_response_date``.

        If the target status is a response status (RESPONDED, NEGOTIATING, ACCEPTED,
        REJECTED) and ``actual_response_date`` has not yet been recorded, today's date
        is stamped automatically.

        Args:
            proposal: Proposal instance to update.
            new_status: One of the ``ProposalStatus`` string values.
            actor: User performing the transition (reserved for future audit log).

        Returns:
            StatusTransitionResult with the old/new status values and a flag
            indicating whether ``actual_response_date`` was set.
        """
        old_status = proposal.status
        response_date_set = False

        if (
            new_status in StatusTransitionService.RESPONSE_STATUSES
            and not proposal.actual_response_date
        ):
            proposal.actual_response_date = timezone.now().date()
            response_date_set = True

        proposal.status = new_status
        proposal.save()

        return StatusTransitionResult(
            success=True,
            old_status=old_status,
            new_status=new_status,
            actual_response_date_set=response_date_set,
        )
