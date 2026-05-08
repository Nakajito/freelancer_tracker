from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.dashboard.services import DashboardService
from apps.exports.services import MonthlySummaryGenerator


class LandingView(TemplateView):
    template_name = "dashboard/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["features"] = [
            {"icon": "bi-file-earmark-text", "title": "Proposal Tracking", "desc": "Track all your proposals in one place"},
            {"icon": "bi-clock", "title": "Time Logging", "desc": "Log hours and monitor billable time"},
            {"icon": "bi-graph-up", "title": "Analytics", "desc": "Analyze your conversion and earnings"},
        ]
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["funnel"] = DashboardService.get_funnel_metrics(user)
        context["conversion"] = DashboardService.get_conversion_metrics(user)
        context["forecast"] = DashboardService.get_forecast_metrics(user)
        context["hourly_rate"] = DashboardService.get_hourly_rate_metrics(user)

        return context


class MonthlySummaryView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/monthly_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        year = int(self.request.GET.get("year", date.today().year))
        month = int(self.request.GET.get("month", date.today().month))

        context["summary"] = MonthlySummaryGenerator.generate(user, year, month)
        context["year"] = year
        context["month"] = month

        return context
