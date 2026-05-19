# Generated for profile preferences.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="avatars/"),
        ),
        migrations.AddField(
            model_name="user",
            name="theme_preference",
            field=models.CharField(
                choices=[
                    ("system", "System"),
                    ("light", "Light"),
                    ("dark", "Dark"),
                ],
                default="system",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="language_preference",
            field=models.CharField(
                choices=[
                    ("en", "English"),
                    ("es", "Español"),
                ],
                default="en",
                max_length=5,
            ),
        ),
    ]
