from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from . import services
from .models import Donation

logger = logging.getLogger(__name__)

DONATION_TIERS = [
    {"label": "Mínimo", "amount": 100, "recommended": False},
    {"label": "Recomendado", "amount": 200, "recommended": True},
    {"label": "Apoyo", "amount": 500, "recommended": False},
    {"label": "Socio", "amount": 1000, "recommended": False},
]


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
        ctx["donation_amount"] = self.request.GET.get("amount", "10.00")
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

        success_url = request.build_absolute_uri(
            reverse("donate_success") + f"?donation_id={donation.pk}"
        )
        failure_url = request.build_absolute_uri(
            reverse("donate_failure") + f"?donation_id={donation.pk}"
        )
        notification_url = request.build_absolute_uri(reverse("donate_webhook_mp"))

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

        init_point = result.get("init_point", "")
        if not init_point:
            logger.error("MP response missing init_point: %s", result)
            return JsonResponse(
                {"error": "No redirect URL from Mercado Pago", "detail": result}, status=502
            )

        return redirect(init_point)


# ---------------------------------------------------------------------------
# Result pages
# ---------------------------------------------------------------------------


class DonateSuccessView(TemplateView):
    template_name = "donations/success.html"

    def get_context_data(self, **kwargs: object) -> dict:
        ctx = super().get_context_data(**kwargs)
        donation_id = self.request.GET.get("donation_id")
        if donation_id:
            ctx["donation"] = get_object_or_404(Donation, pk=donation_id)
        return ctx


class DonateFailureView(TemplateView):
    template_name = "donations/failure.html"

    def get_context_data(self, **kwargs: object) -> dict:
        ctx = super().get_context_data(**kwargs)
        donation_id = self.request.GET.get("donation_id")
        if donation_id:
            ctx["donation"] = get_object_or_404(Donation, pk=donation_id)
        return ctx


# ---------------------------------------------------------------------------
# Webhooks (CSRF exempt — verified via provider signature)
# ---------------------------------------------------------------------------


@method_decorator(csrf_exempt, name="dispatch")
class MPWebhookView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        try:
            data: dict = json.loads(request.body)
        except json.JSONDecodeError:
            data = dict(request.POST)

        try:
            services.handle_mp_webhook(data)
        except Exception as exc:
            logger.error("MP webhook error: %s", exc)
            return HttpResponse(status=400)

        return HttpResponse(status=200)
