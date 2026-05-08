from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.proposals.models import Proposal


class FollowUp(TimeStampedModel):
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

    def mark_completed(self):
        from django.utils import timezone

        self.completed = True
        self.completed_at = timezone.now()
        self.save()
