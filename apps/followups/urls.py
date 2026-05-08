from django.urls import path

from . import views

urlpatterns = [
    path("followups/", views.FollowUpListView.as_view(), name="followup-list"),
    path(
        "followups/create/", views.FollowUpCreateView.as_view(), name="followup-create"
    ),
    path(
        "followups/<int:pk>/complete/",
        views.FollowUpCompleteView.as_view(),
        name="followup-complete",
    ),
    path(
        "followups/<int:pk>/delete/",
        views.FollowUpDeleteView.as_view(),
        name="followup-delete",
    ),
]
