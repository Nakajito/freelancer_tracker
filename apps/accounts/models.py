"""Custom user model with profile and preference fields."""

import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.validators import validate_avatar


def avatar_upload_path(instance, filename: str) -> str:
    """Store under a random name.

    The client-supplied filename was previously kept as-is, which leaks
    whatever the uploader named the file and makes stored paths guessable.
    """
    suffix = Path(filename).suffix.lower()[:10]
    return f"avatars/{uuid.uuid4().hex}{suffix}"


class User(AbstractUser):
    """Application user; email is the canonical login identifier."""

    class ThemePreference(models.TextChoices):
        SYSTEM = "system", _("System")
        LIGHT = "light", _("Light")
        DARK = "dark", _("Dark")

    class LanguagePreference(models.TextChoices):
        EN = "en", _("English")
        ES = "es", _("Español")

    email = models.EmailField(unique=True)
    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True,
        validators=[validate_avatar],
    )
    theme_preference = models.CharField(
        max_length=10,
        choices=ThemePreference.choices,
        default=ThemePreference.SYSTEM,
    )
    language_preference = models.CharField(
        max_length=5,
        choices=LanguagePreference.choices,
        default=LanguagePreference.EN,
    )

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email
