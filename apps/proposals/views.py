import calendar
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.core.mixins import OwnerQuerysetMixin
from apps.proposals.forms import ProposalForm
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus


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

        year = self.request.GET.get("year")
        month = self.request.GET.get("month")
        date_field = self.request.GET.get("date_field", "sent_date")

        if year and month:
            try:
                y, m = int(year), int(month)
            except ValueError, TypeError:
                return qs
            if date_field == "sent_date":
                qs = qs.filter(
                    Q(sent_date__year=y, sent_date__month=m)
                    | Q(sent_date__isnull=True, created_at__year=y, created_at__month=m)
                )
            else:
                qs = qs.filter(created_at__year=y, created_at__month=m)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = list(ProposalStatus.choices)
        context["platform_choices"] = list(Platform.choices)

        today = date.today()
        context["year_choices"] = list(range(today.year, today.year - 5, -1))
        context["month_choices"] = [(i, calendar.month_name[i]) for i in range(1, 13)]
        context["selected_year"] = self.request.GET.get("year", "")
        context["selected_month"] = self.request.GET.get("month", "")
        context["selected_date_field"] = self.request.GET.get("date_field", "sent_date")
        return context


class ProposalDetailView(OwnerQuerysetMixin, DetailView):
    model = Proposal
    template_name = "proposals/proposal_detail.html"


class ProposalCreateView(LoginRequiredMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "proposals/proposal_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("proposal-detail", kwargs={"pk": self.object.pk})


class ProposalUpdateView(OwnerQuerysetMixin, UpdateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "proposals/proposal_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

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


class SearchView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        proposals: list = []
        clients: list = []
        if len(q) >= 2:
            proposals = list(
                Proposal.objects.for_user(request.user).search(q).with_client()[:6]
            )
            clients = list(
                Client.objects.filter(owner=request.user).filter(
                    Q(name__icontains=q) | Q(email__icontains=q)
                )[:4]
            )
        return render(
            request,
            "proposals/search_results.html",
            {"proposals": proposals, "clients": clients, "q": q},
        )
