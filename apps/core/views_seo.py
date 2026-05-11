from django.contrib.sites.models import Site
from django.http import HttpResponse
from django.views import View
from django.views.decorators.cache import cache_page


@cache_page(60 * 60 * 24)
def robots_txt(request):
    try:
        site = Site.objects.get_current()
        domain = site.domain
    except Exception:
        domain = request.get_host()

    body = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /accounts/\n"
        "Disallow: /api/\n"
        "Disallow: /healthz\n"
        "Disallow: /.well-known/\n"
        f"Sitemap: https://{domain}/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain")


@cache_page(60 * 60 * 24)
def security_txt(request):
    try:
        site = Site.objects.get_current()
        domain = site.domain
    except Exception:
        domain = request.get_host()

    body = (
        "Contact: mailto:security@dabg.dev\n"
        "Expires: 2027-05-10T00:00:00.000Z\n"
        "Preferred-Languages: es, en\n"
        f"Canonical: https://{domain}/.well-known/security.txt\n"
    )
    return HttpResponse(body, content_type="text/plain")


class ChangePasswordRedirect(View):
    def get(self, request):
        from django.shortcuts import redirect

        return redirect("/accounts/password/change/", permanent=False)
