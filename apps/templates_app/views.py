from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.core.mixins import OwnerQuerysetMixin
from apps.proposals.models import Client
from apps.templates_app.models import ProposalTemplate
from apps.templates_app.services import PlaceholderRenderer


class TemplateListView(OwnerQuerysetMixin, ListView):
    model = ProposalTemplate
    template_name = "templates_app/template_list.html"
    context_object_name = "templates"


class TemplateCreateView(LoginRequiredMixin, CreateView):
    model = ProposalTemplate
    template_name = "templates_app/template_form.html"
    fields = ["name", "body"]

    def form_valid(self, form):
        form.instance.owner = self.request.user
        placeholders = PlaceholderRenderer.extract_placeholders(form.instance.body)
        form.instance.placeholders = placeholders
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("template-detail", kwargs={"pk": self.object.pk})


class TemplateDetailView(OwnerQuerysetMixin, DetailView):
    model = ProposalTemplate
    template_name = "templates_app/template_detail.html"


class TemplateUpdateView(OwnerQuerysetMixin, UpdateView):
    model = ProposalTemplate
    template_name = "templates_app/template_form.html"
    fields = ["name", "body"]

    def form_valid(self, form):
        placeholders = PlaceholderRenderer.extract_placeholders(form.instance.body)
        form.instance.placeholders = placeholders
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("template-detail", kwargs={"pk": self.object.pk})


class TemplatePreviewView(LoginRequiredMixin, DetailView):
    model = ProposalTemplate
    template_name = "templates_app/template_preview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = self.object

        client_name = self.request.GET.get("client", "Client Name")
        project_title = self.request.GET.get("project", "Project Title")
        amount = self.request.GET.get("amount", "$1,000")

        context["rendered"] = PlaceholderRenderer.render(
            template.body,
            PlaceholderRenderer.build_context(client_name, project_title, amount),
        )
        return context


class TemplateUseView(LoginRequiredMixin, DetailView):
    model = ProposalTemplate
    template_name = "templates_app/template_use.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["clients"] = Client.objects.filter(owner=self.request.user)
        return context


class TemplateDeleteView(OwnerQuerysetMixin, DeleteView):
    model = ProposalTemplate
    template_name = "templates_app/template_confirm_delete.html"
    success_url = reverse_lazy("template-list")
