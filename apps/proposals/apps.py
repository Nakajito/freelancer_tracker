from django.apps import AppConfig


class ProposalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.proposals"
    verbose_name = "Proposals"

    def ready(self):
        from . import signals  # noqa: F401
