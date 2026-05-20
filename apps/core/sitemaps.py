from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return [
            "account_login",
            "account_signup",
            "privacy_policy",
            "terms_of_service",
            "security",
            "donate",
        ]

    def location(self, item):
        return reverse(item)
