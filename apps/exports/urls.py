from django.urls import path

from . import api_views

urlpatterns = [
    path(
        "api/webhooks/proposal-events/",
        api_views.webhook_proposal_events,
        name="webhook-proposal-events",
    ),
]
