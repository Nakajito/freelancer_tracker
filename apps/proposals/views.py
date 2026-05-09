from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.core.mixins import OwnerQuerysetMixin
from apps.proposals.forms import ProposalForm
from apps.proposals.models import Client, Proposal


class ProposalListView(OwnerQuerysetMixin, ListView):
    model = Proposal
    template_name = "proposals/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().with_client().with_tags()
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        platform = self.request.GET.get("platform")
        if platform:
            qs = qs.filter(platform=platform)
        return qs


class ProposalDetailView(OwnerQuerysetMixin, DetailView):
    model = Proposal
    template_name = "proposals/proposal_detail.html"


class ProposalCreateView(LoginRequiredMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "proposals/proposal_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("proposal-detail", kwargs={"pk": self.object.pk})


class ProposalUpdateView(OwnerQuerysetMixin, UpdateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "proposals/proposal_form.html"

    def get_success_url(self):
        return reverse_lazy("proposal-detail", kwargs={"pk": self.object.pk})


class ProposalDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Proposal
    template_name = "proposals/proposal_confirm_delete.html"
    success_url = reverse_lazy("proposal-list")


class ClientListView(OwnerQuerysetMixin, ListView):
    model = Client
    template_name = "proposals/client_list.html"
    context_object_name = "clients"


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    template_name = "proposals/client_form.html"
    fields = ["name", "email", "notes"]

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("client-list")


class ClientDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Client
    template_name = "proposals/client_confirm_delete.html"
    success_url = reverse_lazy("client-list")
