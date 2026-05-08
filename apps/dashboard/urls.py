from django.urls import path

from . import views

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "monthly-summary/", views.MonthlySummaryView.as_view(), name="monthly-summary"
    ),
]
