"""Time tracking models: individual entries and recurring retainers."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.proposals.models import Proposal, ProposalStatus


class TimeEntry(TimeStampedModel):
    """Hours logged against a proposal on a given date."""


    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    date = models.DateField()
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    description = models.TextField(blank=True, default="")
    billable = models.BooleanField(default=True)
    override_status_restriction = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.hours}h on {self.proposal.title}"

    def clean(self):
        if not self.override_status_restriction:
            if self.proposal.status != ProposalStatus.ACCEPTED:
                raise ValidationError(
                    "Time entries can only be added to accepted proposals. "
                    "Use override_status_restriction=True to bypass this check."
                )


class RecurringRetainer(TimeStampedModel):
    """Monthly recurring time commitment tied to an accepted proposal."""

    proposal = models.OneToOneField(
        Proposal,
        on_delete=models.CASCADE,
        related_name="retainer",
    )
    monthly_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    day_of_month = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Retainer for {self.proposal.title}: {self.monthly_hours}h/month"
