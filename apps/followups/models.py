"""Follow-up tasks scheduled against pending proposals."""

from django.db import models

from apps.core.models import TimeStampedModel
from apps.proposals.models import Proposal


class FollowUp(TimeStampedModel):
    """A reminder to nudge a client about a specific proposal."""

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="followups",
    )
    description = models.TextField()
    due_date = models.DateField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["due_date", "completed"]),
        ]
        ordering = ["due_date"]

    def __str__(self):
        return f"Follow-up for {self.proposal.title}"

    @property
    def is_overdue(self) -> bool:
        """``True`` if the follow-up is still pending past its ``due_date``."""
        from django.utils import timezone

        return not self.completed and self.due_date < timezone.now().date()

    def mark_completed(self):
        """Mark this follow-up done and stamp ``completed_at``."""
        from django.utils import timezone

        self.completed = True
        self.completed_at = timezone.now()
        self.save()
