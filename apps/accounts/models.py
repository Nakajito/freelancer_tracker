"""Custom user model with a unique-email constraint."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user; email is the canonical login identifier."""

    email = models.EmailField(unique=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email
