from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core import signing
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from . import services
from .models import Donation
from .webhook_security import WebhookVerificationError, verify_mp_webhook

logger = logging.getLogger(__name__)

DONATION_TIERS = [
    {"label": "Mínimo", "amount": 100, "usd_ref": 5, "recommended": False},
    {"label": "Recomendado", "amount": 200, "usd_ref": 10, "recommended": True},
    {"label": "Apoyo", "amount": 500, "usd_ref": 30, "recommended": False},
    {"label": "Socio", "amount": 1000, "usd_ref": 50, "recommended": False},
]


def _callback_url(request: HttpRequest, path: str) -> str:
    """Build an absolute callback URL for MP.

    Prefers MERCADOPAGO_PUBLIC_BASE_URL when set (local dev behind localhost,
    where MP rejects non-public back_urls); falls back to the request host.
    """
    base = settings.MERCADOPAGO_PUBLIC_BASE_URL
    if base:
        return base.rstrip("/") + path
    return request.build_absolute_uri(path)


DONATION_TOKEN_SALT = "donations.callback"
DONATION_TOKEN_MAX_AGE = 60 * 60 * 24  # 24h — callbacks are followed immediately


# A donation is an anonymous record with no owner to check against, so the
# callback URL carries a signed token instead of the raw pk. With the pk,
# ?donation_id=1,2,3... enumerated every donation's amount, provider and
# status, and the row also holds the donor's email address.
def _donation_token(donation: Donation) -> str:
    return signing.dumps({"pk": donation.pk}, salt=DONATION_TOKEN_SALT)


def _donation_from_token(request: HttpRequest) -> Donation | None:
    token = request.GET.get("t", "")
    if not token:
        return None
    try:
        payload = signing.loads(
            token, salt=DONATION_TOKEN_SALT, max_age=DONATION_TOKEN_MAX_AGE
        )
    except signing.BadSignature:
        raise Http404("Invalid or expired donation reference") from None
    return Donation.objects.filter(pk=payload["pk"]).first()


def _parse_amount(request: HttpRequest) -> Decimal:
    raw_custom = request.POST.get("custom_amount") or request.GET.get("custom_amount")
    raw_amount = request.POST.get("amount") or request.GET.get("amount")
    try:
        custom = Decimal(raw_custom) if raw_custom else None
        amount = Decimal(raw_amount) if raw_amount else None
        return services.validate_donation_amount(amount, custom)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid amount") from exc


class DonateView(TemplateView):
    template_name = "donate.html"

    def get_context_data(self, **kwargs: object) -> dict:
        ctx = super().get_context_data(**kwargs)
        ctx["donation_tiers"] = DONATION_TIERS
        return ctx


class DonateConfirmView(TemplateView):
    template_name = "donate_confirm.html"

    def get_context_data(self, **kwargs: object) -> dict:
        ctx = super().get_context_data(**kwargs)
        custom = (self.request.GET.get("custom_amount") or "").strip()
        ctx["donation_amount"] = custom or self.request.GET.get("amount", "10.00")
        ctx["donation_frequency"] = self.request.GET.get("frequency", "one_time")
        return ctx


# ---------------------------------------------------------------------------
# Mercado Pago
# ---------------------------------------------------------------------------


class DonateMPCreateView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            return JsonResponse({"error": "Mercado Pago not configured"}, status=503)

        try:
            amount = _parse_amount(request)
        except ValueError:
            return JsonResponse({"error": "Invalid amount"}, status=400)

        frequency = request.POST.get("frequency", Donation.FREQUENCY_ONE_TIME)
        email = request.POST.get("email", "")
        currency = request.POST.get("currency", "ARS")

        donation = Donation.objects.create(
            amount=amount,
            currency=currency,
            frequency=frequency,
            provider=Donation.PROVIDER_MP,
            email=email,
        )

        token = _donation_token(donation)
        success_url = _callback_url(request, reverse("donate_success") + f"?t={token}")
        failure_url = _callback_url(request, reverse("donate_failure") + f"?t={token}")
        notification_url = _callback_url(request, reverse("donate_webhook_mp"))

        try:
            if frequency == Donation.FREQUENCY_MONTHLY:
                result = services.create_mp_preapproval(
                    donation,
                    back_url=success_url,
                    notification_url=notification_url,
                )
            else:
                result = services.create_mp_preference(
                    donation,
                    back_urls={
                        "success": success_url,
                        "failure": failure_url,
                        "pending": success_url,
                    },
                    notification_url=notification_url,
                )
        except Exception as exc:
            logger.error("MP error creating payment: %s", exc)
            donation.status = Donation.STATUS_FAILED
            donation.save(update_fields=["status"])
            return JsonResponse({"error": "Payment provider error"}, status=502)

        donation.provider_pref_id = result.get("id", "")
        donation.save(update_fields=["provider_pref_id"])

        # sandbox.mercadopago.com.* is deprecated and causes ERR_TOO_MANY_REDIRECTS.
        # Always use init_point; MP routes test tokens through the test environment.
        init_point = result.get("init_point", "")
        if not init_point:
            logger.error("MP response missing init_point: %s", result)
            return JsonResponse(
                {"error": "No redirect URL from Mercado Pago"}, status=502
            )

        return redirect(init_point)


# ---------------------------------------------------------------------------
# Result pages
# ---------------------------------------------------------------------------


class _DonationCallbackView(TemplateView):
    """Renders a donation identified by a signed token, never by raw pk."""

    def get_context_data(self, **kwargs: object) -> dict:
        ctx = super().get_context_data(**kwargs)
        donation = _donation_from_token(self.request)
        if donation is not None:
            ctx["donation"] = donation
        return ctx


class DonateSuccessView(_DonationCallbackView):
    template_name = "donations/success.html"


class DonateFailureView(_DonationCallbackView):
    template_name = "donations/failure.html"


# ---------------------------------------------------------------------------
# Webhooks
#
# CSRF-exempt because the caller is Mercado Pago, not a browser session. That
# is only safe because every request is authenticated by its x-signature HMAC
# below -- the previous version claimed this in a comment but verified nothing.
# ---------------------------------------------------------------------------


@method_decorator(csrf_exempt, name="dispatch")
class MPWebhookView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        try:
            data: dict = json.loads(request.body)
        except json.JSONDecodeError:
            data = dict(request.POST)

        # MP signs the resource id from the query string; fall back to the body
        # so both notification shapes verify against the same manifest.
        data_id = request.GET.get("data.id") or str(
            (data.get("data") or {}).get("id") or data.get("id") or ""
        )

        try:
            verify_mp_webhook(request, data_id)
        except WebhookVerificationError as exc:
            logger.warning("Rejected unsigned MP webhook: %s", exc)
            return HttpResponse(status=401)

        try:
            services.handle_mp_webhook(data)
        except Exception as exc:
            logger.error("MP webhook error: %s", exc)
            return HttpResponse(status=400)

        return HttpResponse(status=200)
