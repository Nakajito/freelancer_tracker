from django.urls import path

from . import api_views, views

urlpatterns = [
    path("proposals/", views.ProposalListView.as_view(), name="proposal-list"),
    path(
        "proposals/create/", views.ProposalCreateView.as_view(), name="proposal-create"
    ),
    path(
        "proposals/<int:pk>/",
        views.ProposalDetailView.as_view(),
        name="proposal-detail",
    ),
    path(
        "proposals/<int:pk>/edit/",
        views.ProposalUpdateView.as_view(),
        name="proposal-update",
    ),
    path(
        "proposals/<int:pk>/delete/",
        views.ProposalDeleteView.as_view(),
        name="proposal-delete",
    ),
    path("clients/", views.ClientListView.as_view(), name="client-list"),
    path("clients/create/", views.ClientCreateView.as_view(), name="client-create"),
    path(
        "api/proposals/duplicate-check/",
        api_views.duplicate_check,
        name="duplicate-check",
    ),
    path(
        "api/proposals/export/json/",
        api_views.proposal_export_json,
        name="proposal-export-json",
    ),
    path(
        "api/proposals/export/csv/",
        api_views.proposal_export_csv,
        name="proposal-export-csv",
    ),
]
