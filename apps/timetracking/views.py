from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.mixins import ProposalOwnerQuerysetMixin
from apps.proposals.models import Proposal, ProposalStatus
from apps.timetracking.forms import TimeEntryForm, TimeEntryUpdateForm
from apps.timetracking.models import RecurringRetainer, TimeEntry
from apps.timetracking.services import BillableAggregationService


class TimeEntryListView(ProposalOwnerQuerysetMixin, ListView):
    model = TimeEntry
    template_name = "timetracking/timeentry_list.html"
    context_object_name = "time_entries"

    def get_queryset(self):
        return super().get_queryset().select_related("proposal", "proposal__client")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = BillableAggregationService.get_weekly_summary(self.request.user)
        context.update(summary)
        return context


class TimeEntryCreateView(LoginRequiredMixin, CreateView):
    model = TimeEntry
    form_class = TimeEntryForm
    template_name = "timetracking/timeentry_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["proposal"].queryset = Proposal.objects.for_user(
            self.request.user
        ).filter(status=ProposalStatus.ACCEPTED)
        return form

    def get_success_url(self):
        return reverse("timeentry-list")


class TimeEntryUpdateView(ProposalOwnerQuerysetMixin, UpdateView):
    model = TimeEntry
    form_class = TimeEntryUpdateForm
    template_name = "timetracking/timeentry_form.html"

    def get_success_url(self):
        return reverse("timeentry-list")


class TimeEntryDeleteView(ProposalOwnerQuerysetMixin, DeleteView):
    model = TimeEntry
    template_name = "timetracking/timeentry_confirm_delete.html"
    success_url = reverse_lazy("timeentry-list")


class RecurringRetainerListView(ProposalOwnerQuerysetMixin, ListView):
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
