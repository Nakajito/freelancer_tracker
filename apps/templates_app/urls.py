from django.urls import path

from . import views

urlpatterns = [
    path("templates/", views.TemplateListView.as_view(), name="template-list"),
    path(
        "templates/create/", views.TemplateCreateView.as_view(), name="template-create"
    ),
    path(
        "templates/<int:pk>/",
        views.TemplateDetailView.as_view(),
        name="template-detail",
    ),
    path(
        "templates/<int:pk>/edit/",
        views.TemplateUpdateView.as_view(),
        name="template-update",
    ),
    path(
        "templates/<int:pk>/preview/",
        views.TemplatePreviewView.as_view(),
        name="template-preview",
    ),
    path(
        "templates/<int:pk>/use/", views.TemplateUseView.as_view(), name="template-use"
    ),
    path(
        "templates/<int:pk>/delete/",
        views.TemplateDeleteView.as_view(),
        name="template-delete",
    ),
]
