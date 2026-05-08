from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, View
from django.http import HttpResponseRedirect
from django.utils import timezone

from apps.followups.forms import FollowUpForm
from apps.followups.models import FollowUp
from apps.followups.services import FollowUpQuerySet


class OwnerQuerysetMixin(LoginRequiredMixin):
    def get_queryset(self):
        return super().get_queryset().filter(proposal__owner=self.request.user)


class FollowUpListView(OwnerQuerysetMixin, ListView):
    model = FollowUp
    template_name = "followups/followup_list.html"
    context_object_name = "followups"

    def get_queryset(self):
        qs = super().get_queryset().select_related("proposal", "proposal__client")
        filter_type = self.request.GET.get("filter", "upcoming")
        if filter_type == "overdue":
            return FollowUpQuerySet.overdue(self.request.user)
        elif filter_type == "completed":
            return qs.filter(completed=True)
        return FollowUpQuerySet.upcoming(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["today"] = timezone.now().date()
        context["upcoming_count"] = FollowUpQuerySet.upcoming(user).count()
        context["overdue_count"] = FollowUpQuerySet.overdue(user).count()
        context["completed_count"] = FollowUp.objects.filter(
            proposal__owner=user, completed=True
        ).count()
        context["current_filter"] = self.request.GET.get("filter", "upcoming")
        return context


class FollowUpCreateView(LoginRequiredMixin, CreateView):
    model = FollowUp
    form_class = FollowUpForm
    template_name = "followups/followup_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["proposal"].queryset = form.fields["proposal"].queryset.filter(
            owner=self.request.user
        )
        return form

    def get_success_url(self):
        return reverse("followup-list")


class FollowUpCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        followup = FollowUp.objects.filter(pk=pk, proposal__owner=request.user).first()
        if followup:
            followup.mark_completed()
        return HttpResponseRedirect(reverse("followup-list"))


class FollowUpDeleteView(OwnerQuerysetMixin, DeleteView):
    model = FollowUp
    template_name = "followups/followup_confirm_delete.html"
    success_url = reverse_lazy("followup-list")
