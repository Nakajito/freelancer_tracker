from django.urls import path

from . import views

# i18n routes (mounted inside i18n_patterns)
i18n_urlpatterns = [
    path("donate/", views.DonateView.as_view(), name="donate"),
    path("donate/confirm/", views.DonateConfirmView.as_view(), name="donate_confirm"),
    path(
        "donate/mercadopago/create-preference/",
        views.DonateMPCreateView.as_view(),
        name="donate_mp_preference",
    ),
    path("donate/success/", views.DonateSuccessView.as_view(), name="donate_success"),
    path("donate/failure/", views.DonateFailureView.as_view(), name="donate_failure"),
]

# Non-i18n routes (webhooks — no language prefix)
webhook_urlpatterns = [
    path(
        "donate/webhooks/mercadopago/",
        views.MPWebhookView.as_view(),
        name="donate_webhook_mp",
    ),
]
