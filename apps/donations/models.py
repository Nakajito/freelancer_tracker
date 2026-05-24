from django.db import models

from apps.core.models import TimeStampedModel


class Donation(TimeStampedModel):
    PROVIDER_MP = "mercadopago"
    PROVIDER_CHOICES = [
        (PROVIDER_MP, "Mercado Pago"),
    ]

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    FREQUENCY_ONE_TIME = "one_time"
    FREQUENCY_MONTHLY = "monthly"
    FREQUENCY_CHOICES = [
        (FREQUENCY_ONE_TIME, "One-time"),
        (FREQUENCY_MONTHLY, "Monthly"),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default=FREQUENCY_ONE_TIME
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    provider_payment_id = models.CharField(max_length=255, blank=True)
    # MP preference id (set when preference is created)
    provider_pref_id = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Donation ${self.amount} via {self.provider} [{self.status}]"
