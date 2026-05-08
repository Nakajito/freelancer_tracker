def log_activity(actor, verb, target, **metadata):
    from apps.core.models import ActivityLog

    ActivityLog.objects.create(
        actor=actor,
        verb=verb,
        target=target,
        metadata=metadata,
    )
