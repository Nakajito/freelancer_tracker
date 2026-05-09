"""Reusable view mixins for owner-scoped querysets."""

from django.contrib.auth.mixins import LoginRequiredMixin


class OwnerQuerysetMixin(LoginRequiredMixin):
    """Restrict a CBV queryset to objects owned by ``request.user``.

    Use on models that expose a direct ``owner`` foreign key
    (``Proposal``, ``Client``, ``Tag``, ``ProposalTemplate``).
    """

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class ProposalOwnerQuerysetMixin(LoginRequiredMixin):
    """Restrict a CBV queryset to objects whose related proposal owner is ``request.user``.

    Use on models that reach the user through ``proposal.owner``
    (``FollowUp``, ``TimeEntry``, ``RecurringRetainer``).
    """

    def get_queryset(self):
        return super().get_queryset().filter(proposal__owner=self.request.user)
