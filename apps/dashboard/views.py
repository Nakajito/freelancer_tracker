import json
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from apps.dashboard.services import DashboardService
from apps.exports.services import MonthlySummaryGenerator


class LandingView(TemplateView):
    template_name = "dashboard/landing.html"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["funnel"] = DashboardService.get_funnel_metrics(user)
        context["conversion"] = DashboardService.get_conversion_metrics(user)
        context["forecast"] = DashboardService.get_forecast_metrics(user)
        context["hourly_rate"] = DashboardService.get_hourly_rate_metrics(user)
        context["urgent_followups"] = DashboardService.get_urgent_followups(user)
        context["today"] = timezone.now().date()

        return context


class MonthlySummaryView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/monthly_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        today = date.today()
        year = int(self.request.GET.get("year", today.year))
        month = int(self.request.GET.get("month", today.month))

        summary = MonthlySummaryGenerator.generate(user, year, month)
        chart = DashboardService.get_earnings_chart(user, months=6)

        context["summary"] = summary
        context["year"] = year
        context["month"] = month
        context["chart_labels"] = json.dumps(chart["labels"])
        context["chart_data"] = json.dumps(chart["data"])
        context["platform_conversion"] = DashboardService.get_platform_conversion(
            user, year, month
        )
        context["platform_stats"] = DashboardService.get_platform_stats(
            user, year, month
        )
        context["hourly_rate"] = DashboardService.get_hourly_rate_metrics(user).hourly_rate

        return context
