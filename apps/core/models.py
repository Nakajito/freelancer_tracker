"""Cross-cutting abstract models and the audit ``ActivityLog`` table."""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base that adds ``created_at`` and ``updated_at`` timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OwnedModel(TimeStampedModel):
    """Abstract base for any record scoped to a single user.

    Adds an ``owner`` FK to ``AUTH_USER_MODEL`` so per-user querysets and
    the shared ``OwnerQuerysetMixin`` work uniformly across apps.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
    )

    class Meta:
        abstract = True


class ActivityLog(TimeStampedModel):
    """Audit-trail row recording who did what to which object.

    Uses a generic foreign key so signals from any app can append entries
    without coupling the audit table to specific models.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activity_logs",
    )
    verb = models.CharField(max_length=100)
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("target_content_type", "target_object_id")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["target_content_type", "target_object_id", "-created_at"]
            ),
        ]

    def __str__(self):
        return f"{self.actor} - {self.verb} - {self.target}"
