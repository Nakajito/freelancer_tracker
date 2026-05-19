"""Custom user model with profile and preference fields."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user; email is the canonical login identifier."""

    class ThemePreference(models.TextChoices):
        SYSTEM = "system", "System"
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    class LanguagePreference(models.TextChoices):
        EN = "en", "English"
        ES = "es", "Español"

    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
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
