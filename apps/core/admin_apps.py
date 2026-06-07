from django.contrib.admin.apps import AdminConfig


class SecureAdminConfig(AdminConfig):
    """Replaces the default admin site with one restricted to superusers.

    Lives in its own module (not apps.py) so the imported ``AdminConfig`` base
    class doesn't make the "apps.core" package autodiscovery ambiguous.
    """

    default_site = "apps.core.admin.SecureAdminSite"
