from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.core.signals import log_activity
from apps.proposals.models import Proposal, ProposalStatus


@receiver(pre_save, sender=Proposal)
def proposal_pre_save(sender, instance, **kwargs):
    if instance.pk:
        old = Proposal.objects.get(pk=instance.pk)
        instance._old_status = old.status
    else:
        instance._old_status = None


@receiver(post_save, sender=Proposal)
def proposal_post_save(sender, instance, created, **kwargs):
    if instance._old_status and instance._old_status != instance.status:
        log_activity(
            actor=instance.owner,
            verb=f"changed status from {instance._old_status} to {instance.status}",
            target=instance,
        )

    if created:
        log_activity(
            actor=instance.owner,
            verb="created proposal",
            target=instance,
        )
