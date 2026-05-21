from django.urls import path

from . import views

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "monthly-summary/", views.MonthlySummaryView.as_view(), name="monthly-summary"
    ),
    path("demo/", views.DemoAutoLoginView.as_view(), name="demo-login"),
    path("demo/signup/", views.DemoSignupRedirectView.as_view(), name="demo-signup"),
    path("demo/exit/", views.DemoExitView.as_view(), name="demo-exit"),
]
