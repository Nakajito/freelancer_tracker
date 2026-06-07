from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path
from django.views.generic import TemplateView

from apps.core.views_health import healthz
from apps.core.views_seo import robots_txt, security_txt, ChangePasswordRedirect
from apps.donations.urls import (
    i18n_urlpatterns as donations_i18n,
    webhook_urlpatterns as donations_webhooks,
)
from apps.core.sitemaps import StaticViewSitemap

sitemaps = {"static": StaticViewSitemap}

# Machine-readable routes: no language prefix
urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path(".well-known/security.txt", security_txt, name="security_txt"),
    path(
        ".well-known/change-password",
        ChangePasswordRedirect.as_view(),
        name="change_password",
    ),
    path(settings.ADMIN_URL, admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    *donations_webhooks,
]

# UI routes: language-prefixed (/en/..., /es/...)
urlpatterns += i18n_patterns(
    path(
        "privacy",
        TemplateView.as_view(template_name="privacy.html"),
        name="privacy_policy",
    ),
    path(
        "terms",
        TemplateView.as_view(template_name="terms.html"),
        name="terms_of_service",
    ),
    path(
        "security", TemplateView.as_view(template_name="security.html"), name="security"
    ),
    *donations_i18n,
    path("", include("apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.proposals.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.exports.urls")),
    path("", include("apps.followups.urls")),
    path("", include("apps.timetracking.urls")),
    path("", include("apps.templates_app.urls")),
    prefix_default_language=True,
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
