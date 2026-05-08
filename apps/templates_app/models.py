from django.conf import settings
from django.db import models

from apps.core.models import OwnedModel


class ProposalTemplate(OwnedModel):
    name = models.CharField(max_length=255)
    body = models.TextField()
    placeholders = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
