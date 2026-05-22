"""Proposals app data model: clients, tags, and the proposal record itself."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

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

    def search(self, q: str):
        return self.filter(
            models.Q(title__icontains=q)
            | models.Q(client__name__icontains=q)
            | models.Q(proposal_text__icontains=q)
        )


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

    UPWORK = "upwork", _("Upwork")
    FIVERR = "fiverr", _("Fiverr")
    FREELANCER = "freelancer", _("Freelancer")
    WORKANA = "workana", _("Workana")
    LINKEDIN = "linkedin", _("LinkedIn")
    OTHER = "other", _("Other")


class ProposalStatus(models.TextChoices):
    """Lifecycle states a proposal can move through."""

    DRAFT = "draft", _("Draft")
    SENT = "sent", _("Sent")
    VIEWED = "viewed", _("Viewed")
    RESPONDED = "responded", _("Responded")
    NEGOTIATING = "negotiating", _("Negotiating")
    ACCEPTED = "accepted", _("Accepted")
    REJECTED = "rejected", _("Rejected")
    ARCHIVED = "archived", _("Archived")


class PricingType(models.TextChoices):
    """Billing model for a proposal."""

    FIXED = "fixed", _("Fixed Price")
    HOURLY = "hourly", _("Hourly Rate")


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
        Client,
        on_delete=models.CASCADE,
        related_name="proposals",
        null=True,
        blank=True,
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
    pricing_type = models.CharField(
        max_length=10,
        choices=PricingType.choices,
        default=PricingType.FIXED,
        db_default=PricingType.FIXED,
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    objects = ProposalManager()

    class Meta:
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "platform", "sent_date"]),
            models.Index(fields=["client", "sent_date"]),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # If called with update_fields, include 'amount' to persist the recalculated value.
        if (
            self.pricing_type == PricingType.HOURLY
            and self.hourly_rate is not None
            and self.estimated_hours is not None
        ):
            self.amount = (self.hourly_rate * self.estimated_hours).quantize(
                Decimal("0.01")
            )
        super().save(*args, **kwargs)

    @property
    def is_hourly(self) -> bool:
        return self.pricing_type == PricingType.HOURLY

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
                {"amount": _("Amount must be greater than or equal to 0")}
            )
