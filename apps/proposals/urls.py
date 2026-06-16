from django.urls import path

from . import api_views, views
from .views import SearchView

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("proposals/", views.ProposalListView.as_view(), name="proposal-list"),
    path(
        "proposals/create/", views.ProposalCreateView.as_view(), name="proposal-create"
    ),
    path(
        "proposals/import/",
        views.ProposalImportView.as_view(),
        name="proposal-import",
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
        "clients/<int:pk>/delete/",
        views.ClientDeleteView.as_view(),
        name="client-delete",
    ),
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
