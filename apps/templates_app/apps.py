from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TemplatesAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.templates_app"
    verbose_name = _("Templates")
