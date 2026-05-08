from django.urls import path

from . import views

urlpatterns = [
    path("time-entries/", views.TimeEntryListView.as_view(), name="timeentry-list"),
    path(
        "time-entries/create/",
        views.TimeEntryCreateView.as_view(),
        name="timeentry-create",
    ),
    path(
        "time-entries/<int:pk>/edit/",
        views.TimeEntryUpdateView.as_view(),
        name="timeentry-update",
    ),
    path(
        "time-entries/<int:pk>/delete/",
        views.TimeEntryDeleteView.as_view(),
        name="timeentry-delete",
    ),
    path("retainers/", views.RecurringRetainerListView.as_view(), name="retainer-list"),
    path(
        "retainers/create/",
        views.RecurringRetainerCreateView.as_view(),
        name="retainer-create",
    ),
]
