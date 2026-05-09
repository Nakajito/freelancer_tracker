"""Reusable proposal text templates with placeholder substitution."""

from django.db import models

from apps.core.models import OwnedModel


class ProposalTemplate(OwnedModel):
    """Stored proposal body with named placeholders for fast reuse."""

    name = models.CharField(max_length=255)
    body = models.TextField()
    placeholders = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
