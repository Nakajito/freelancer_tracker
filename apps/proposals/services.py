from datetime import timedelta
from typing import Optional

from django.utils import timezone
from pydantic import BaseModel

from apps.proposals.models import Proposal, ProposalStatus


class DuplicateCheckResult(BaseModel):
    is_duplicate: bool
    existing_proposals: list = []


class StatusTransitionResult(BaseModel):
    success: bool
    old_status: str
    new_status: str
    actual_response_date_set: bool = False


class DuplicateCheckService:
    @staticmethod
    def check_duplicate(
        owner,
        client,
        platform: str,
        days: int = 30,
    ) -> DuplicateCheckResult:
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
