from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FollowupsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.followups"
    verbose_name = _("Follow-ups")
