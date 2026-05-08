from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.proposals.models import Proposal, ProposalStatus
from apps.timetracking.models import RecurringRetainer, TimeEntry


class OwnerQuerysetMixin(LoginRequiredMixin):
    def get_queryset(self):
        return super().get_queryset().filter(proposal__owner=self.request.user)


class TimeEntryListView(OwnerQuerysetMixin, ListView):
    model = TimeEntry
    template_name = "timetracking/timeentry_list.html"
    context_object_name = "time_entries"

    def get_queryset(self):
        return super().get_queryset().select_related("proposal", "proposal__client")


class TimeEntryCreateView(LoginRequiredMixin, CreateView):
    model = TimeEntry
    template_name = "timetracking/timeentry_form.html"
    fields = [
        "proposal",
        "date",
        "hours",
        "description",
        "billable",
        "override_status_restriction",
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["proposal"].queryset = Proposal.objects.for_user(
            self.request.user
        ).filter(status=ProposalStatus.ACCEPTED)
        return form

    def get_success_url(self):
        return reverse("timeentry-list")


class TimeEntryUpdateView(OwnerQuerysetMixin, UpdateView):
    model = TimeEntry
    template_name = "timetracking/timeentry_form.html"
    fields = ["date", "hours", "description", "billable", "override_status_restriction"]

    def get_success_url(self):
        return reverse("timeentry-list")


class TimeEntryDeleteView(OwnerQuerysetMixin, DeleteView):
    model = TimeEntry
    template_name = "timetracking/timeentry_confirm_delete.html"
    success_url = reverse_lazy("timeentry-list")


class RecurringRetainerListView(OwnerQuerysetMixin, ListView):
    model = RecurringRetainer
    template_name = "timetracking/retainer_list.html"
    context_object_name = "retainers"

    def get_queryset(self):
        return super().get_queryset().select_related("proposal", "proposal__client")


class RecurringRetainerCreateView(LoginRequiredMixin, CreateView):
    model = RecurringRetainer
    template_name = "timetracking/retainer_form.html"
    fields = ["proposal", "monthly_hours", "day_of_month", "active"]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["proposal"].queryset = Proposal.objects.for_user(
            self.request.user
        ).filter(status=ProposalStatus.ACCEPTED)
        return form

    def get_success_url(self):
        return reverse("retainer-list")
