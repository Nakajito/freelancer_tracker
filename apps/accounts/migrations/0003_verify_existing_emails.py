"""Grandfather existing accounts into mandatory email verification.

ACCOUNT_EMAIL_VERIFICATION moved from allauth's "optional" default to
"mandatory". Users created before allauth was wired in (or through
``createsuperuser`` / ``create_user``, which never touch allauth) have no
``EmailAddress`` row, so without this they would all be locked out on deploy.

Their addresses are marked verified because they were already usable logins --
this preserves the status quo for existing accounts while requiring genuine
verification from every new signup.
"""

from django.db import migrations


def create_verified_email_addresses(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")

    existing = set(EmailAddress.objects.values_list("user_id", flat=True).distinct())

    to_create = [
        EmailAddress(user_id=user.pk, email=user.email, verified=True, primary=True)
        for user in User.objects.exclude(email="").iterator()
        if user.pk not in existing
    ]
    EmailAddress.objects.bulk_create(to_create, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    """Intentionally irreversible in effect.

    Deleting these rows would lock the same users out again; leaving them is
    harmless if ACCOUNT_EMAIL_VERIFICATION is reverted.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_profile_preferences"),
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_verified_email_addresses, noop_reverse),
    ]
