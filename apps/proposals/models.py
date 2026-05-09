"""Proposals app data model: clients, tags, and the proposal record itself."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import OwnedModel


class ProposalQuerySet(models.QuerySet):
    """Chainable queryset filters used by ``ProposalManager`` and views."""

    def for_user(self, user):
        """Restrict to proposals owned by ``user``."""
        return self.filter(owner=user)

    def pending_response(self):
        """Restrict to proposals awaiting a client reply (``SENT``/``VIEWED``)."""
        return self.filter(
            status__in=[
                ProposalStatus.SENT,
                ProposalStatus.VIEWED,
            ]
        )

    def with_client(self):
        """Eager-load the related ``Client`` row."""
        return self.select_related("client")

    def with_tags(self):
        """Eager-load the M2M tags collection."""
        return self.prefetch_related("tags")

    def accepted(self):
        """Restrict to proposals with status ``ACCEPTED``."""
        return self.filter(status=ProposalStatus.ACCEPTED)


class ProposalManager(models.Manager):
    """Default manager that exposes ``ProposalQuerySet`` filters."""

    def get_queryset(self):
        return ProposalQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def pending_response(self):
        return self.get_queryset().pending_response()

    def with_client(self):
        return self.get_queryset().with_client()

    def with_tags(self):
        return self.get_queryset().with_tags()

    def accepted(self):
        return self.get_queryset().accepted()


class Platform(models.TextChoices):
    """Sourcing platform a proposal originates from."""

    UPWORK = "upwork", "Upwork"
    FIVERR = "fiverr", "Fiverr"
    FREELANCER = "freelancer", "Freelancer"
    WORKANA = "workana", "Workana"
    LINKEDIN = "linkedin", "LinkedIn"
    OTHER = "other", "Other"


class ProposalStatus(models.TextChoices):
    """Lifecycle states a proposal can move through."""

    DRAFT = "draft", "Draft"
    SENT = "sent", "Sent"
    VIEWED = "viewed", "Viewed"
    RESPONDED = "responded", "Responded"
    NEGOTIATING = "negotiating", "Negotiating"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class Client(OwnedModel):
    """A client (or prospect) the freelancer pitches to."""

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_client_name"
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(OwnedModel):
    """User-defined label used to group proposals."""

    slug = models.SlugField(max_length=50)
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "slug"], name="unique_tag_slug"),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Proposal(OwnedModel):
    """A pitch the freelancer sent to a client on a given platform.

    Tracks lifecycle, monetary value, expected vs actual response timing,
    and tags. Conversion metrics in the dashboard derive from this model.
    """

    title = models.CharField(max_length=255)
    platform = models.CharField(
        max_length=20, choices=Platform.choices, default=Platform.OTHER
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="proposals", null=True, blank=True
    )
    proposal_text = models.TextField(blank=True, default="")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20, choices=ProposalStatus.choices, default=ProposalStatus.DRAFT
    )
    sent_date = models.DateField(null=True, blank=True)
    expected_response_date = models.DateField(null=True, blank=True)
    actual_response_date = models.DateField(null=True, blank=True)
    job_url = models.URLField(max_length=500, blank=True, default="")
    proposal_url = models.URLField(max_length=500, blank=True, default="")
    tags = models.ManyToManyField(Tag, blank=True, related_name="proposals")
    paid = models.BooleanField(default=False)

    objects = ProposalManager()

    class Meta:
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "platform", "sent_date"]),
            models.Index(fields=["client", "sent_date"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        client_name = self.client.name if self.client_id else "—"
        return f"{self.title} - {client_name}"

    @property
    def response_time(self):
        """Days between ``sent_date`` and ``actual_response_date``, or ``None``."""
        if self.sent_date and self.actual_response_date:
            return (self.actual_response_date - self.sent_date).days
        return None

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.amount and self.amount < 0:
            raise ValidationError(
                {"amount": "Amount must be greater than or equal to 0"}
            )
