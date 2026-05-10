from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return ["accounts:login", "accounts:signup"]

    def location(self, item):
        return reverse(item)