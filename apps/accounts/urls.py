from django.urls import path

from apps.accounts import views


urlpatterns = [
    path("accounts/profile/", views.ProfileView.as_view(), name="account-profile"),
    path(
        "accounts/preferences/",
        views.PreferencesView.as_view(),
        name="account-preferences",
    ),
    path(
        "accounts/deactivate/",
        views.DeactivateAccountView.as_view(),
        name="account-deactivate",
    ),
]
