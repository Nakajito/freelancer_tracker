from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.conf import settings

from apps.core.views_health import healthz
from apps.core.views_seo import robots_txt, security_txt, ChangePasswordRedirect
from apps.core.sitemaps import StaticViewSitemap

sitemaps = {"static": StaticViewSitemap}

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path(".well-known/security.txt", security_txt, name="security_txt"),
    path(".well-known/change-password", ChangePasswordRedirect.as_view(), name="change_password"),
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
