from django.contrib import admin
from django.urls import include, path
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.proposals.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.exports.urls")),
    path("", include("apps.followups.urls")),
    path("", include("apps.timetracking.urls")),
    path("", include("apps.templates_app.urls")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
