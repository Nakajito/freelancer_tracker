from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProposalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.proposals"
    verbose_name = _("Proposals")

    def ready(self):
        from . import signals  # noqa: F401
