from django.contrib.admin import AdminSite


class SecureAdminSite(AdminSite):
    """Admin site restricted to active superusers.

    Django's default ``has_permission`` grants access to any active staff
    member. We tighten it to superusers only, so a compromised staff account
    cannot reach the admin.
    """

    def has_permission(self, request):
        user = request.user
        return user.is_active and user.is_superuser
