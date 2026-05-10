import json
from datetime import date, timedelta

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
        period = self.request.GET.get("period", "90")
        year = int(self.request.GET.get("year", today.year))

        if period == "30":
            start_date = today - timedelta(days=30)
            end_date = today + timedelta(days=1)
            period_label = "Last 30 Days"
        elif period == "year":
            start_date = date(year, 1, 1)
            end_date = date(year + 1, 1, 1)
            period_label = str(year)
        else:  # "90" default
            start_date = today - timedelta(days=90)
            end_date = today + timedelta(days=1)
            period_label = "Last 90 Days"

        summary = MonthlySummaryGenerator.generate(user, start_date, end_date, period_label)
        chart = DashboardService.get_earnings_chart(user, months=6)

        context["summary"] = summary
        context["year"] = year
        context["period"] = period
        context["chart_labels"] = json.dumps(chart["labels"])
        context["chart_data"] = json.dumps(chart["data"])
        context["platform_conversion"] = DashboardService.get_platform_conversion(
            user, start_date, end_date
        )
        context["platform_stats"] = DashboardService.get_platform_stats(
            user, start_date, end_date
        )
        context["hourly_rate"] = DashboardService.get_hourly_rate_metrics(
            user
        ).hourly_rate

        return context
