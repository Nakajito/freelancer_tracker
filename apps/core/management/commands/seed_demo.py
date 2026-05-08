import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.followups.models import FollowUp
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus, Tag
from apps.templates_app.models import ProposalTemplate
from apps.timetracking.models import RecurringRetainer, TimeEntry


CLIENTS = [
    ("Acme Corp", "contact@acme.com"),
    ("Globex", "hello@globex.io"),
    ("Initech", "ops@initech.com"),
    ("Hooli", "team@hooli.xyz"),
    ("Stark Industries", "tony@stark.com"),
]

PROJECT_TYPES = [
    "Web App",
    "REST API",
    "Landing Page",
    "Admin Dashboard",
    "Mobile Backend",
    "E-commerce Store",
    "Marketing Site",
    "Data Pipeline",
]

TEMPLATE_BODIES = [
    (
        "Web Application Pitch",
        "Hi {client},\n\nThanks for considering me for {project}. "
        "Based on the scope, I estimate {amount} for the build.\n\n"
        "Sending this on {date}. Looking forward to your feedback.",
    ),
    (
        "Hourly Engagement",
        "Hi {client},\n\nProposing an hourly engagement for {project} at {amount}/hr.\n"
        "Start date target: {date}.\n\nLet me know if this works.",
    ),
    (
        "Retainer Proposal",
        "Hi {client},\n\nProposing a monthly retainer for {project} at {amount}/month.\n"
        "Effective {date}. Includes priority support and async updates.",
    ),
]


class Command(BaseCommand):
    help = "Seeds the database with demo data (idempotent; --reset truncates first)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete demo user's existing data before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            email="demo@propotrack.test",
            defaults={"username": "demo", "first_name": "Demo", "last_name": "User"},
        )
        user.set_password("demo1234")
        user.save()

        if options["reset"]:
            self.stdout.write("Resetting demo user's data…")
            Proposal.objects.filter(owner=user).delete()
            Client.objects.filter(owner=user).delete()
            Tag.objects.filter(owner=user).delete()
            ProposalTemplate.objects.filter(owner=user).delete()

        clients = []
        for name, email in CLIENTS:
            client, _ = Client.objects.get_or_create(
                owner=user, name=name, defaults={"email": email}
            )
            clients.append(client)

        tag_django, _ = Tag.objects.get_or_create(
            owner=user, slug="django", defaults={"name": "Django"}
        )
        tag_react, _ = Tag.objects.get_or_create(
            owner=user, slug="react", defaults={"name": "React"}
        )
        tag_urgent, _ = Tag.objects.get_or_create(
            owner=user, slug="urgent", defaults={"name": "Urgent"}
        )
        tags = [tag_django, tag_react, tag_urgent]

        statuses = [
            ProposalStatus.DRAFT,
            ProposalStatus.SENT,
            ProposalStatus.VIEWED,
            ProposalStatus.RESPONDED,
            ProposalStatus.NEGOTIATING,
            ProposalStatus.ACCEPTED,
            ProposalStatus.ACCEPTED,
            ProposalStatus.ACCEPTED,
            ProposalStatus.REJECTED,
        ]
        platforms = [p[0] for p in Platform.choices]

        proposals_created = 0
        accepted_proposals = []
        for i in range(25):
            days_ago = random.randint(1, 180)
            sent_date = date.today() - timedelta(days=days_ago)
            status = random.choice(statuses)
            proposal = Proposal.objects.create(
                owner=user,
                title=f"{random.choice(PROJECT_TYPES)} - Sprint {i + 1}",
                platform=random.choice(platforms),
                client=random.choice(clients),
                proposal_text=(
                    f"Pitch for {random.choice(PROJECT_TYPES).lower()}. "
                    "Estimated 4 weeks delivery."
                ),
                amount=Decimal(random.randint(500, 8000)),
                status=status,
                sent_date=sent_date,
                expected_response_date=sent_date + timedelta(days=7),
            )
            proposal.tags.add(random.choice(tags))

            if status in (
                ProposalStatus.RESPONDED,
                ProposalStatus.NEGOTIATING,
                ProposalStatus.ACCEPTED,
                ProposalStatus.REJECTED,
            ):
                proposal.actual_response_date = sent_date + timedelta(
                    days=random.randint(1, 14)
                )
                if status == ProposalStatus.ACCEPTED:
                    proposal.paid = random.random() > 0.5
                proposal.save()

            if status == ProposalStatus.ACCEPTED:
                accepted_proposals.append(proposal)
            proposals_created += 1

        followups_created = 0
        pending_proposals = list(
            Proposal.objects.filter(
                owner=user,
                status__in=[ProposalStatus.SENT, ProposalStatus.VIEWED],
            )
        )
        for proposal in pending_proposals[:10]:
            offset = random.randint(-7, 7)
            FollowUp.objects.create(
                proposal=proposal,
                description=f"Check in on {proposal.title}",
                due_date=date.today() + timedelta(days=offset),
                completed=offset < -5,
            )
            followups_created += 1

        time_entries_created = 0
        for proposal in accepted_proposals:
            for _ in range(random.randint(3, 8)):
                entry_date = date.today() - timedelta(days=random.randint(1, 42))
                TimeEntry.objects.create(
                    proposal=proposal,
                    date=entry_date,
                    hours=Decimal(random.choice(["1.0", "1.5", "2.0", "3.5", "4.0"])),
                    description=random.choice(
                        ["Implementation", "Code review", "Bugfix", "Meeting", "QA"]
                    ),
                    billable=random.random() > 0.3,
                )
                time_entries_created += 1

        retainers_created = 0
        if accepted_proposals:
            target = accepted_proposals[0]
            if not hasattr(target, "retainer"):
                RecurringRetainer.objects.create(
                    proposal=target,
                    monthly_hours=Decimal("20.00"),
                    day_of_month=1,
                    active=True,
                )
                retainers_created = 1

        templates_created = 0
        for name, body in TEMPLATE_BODIES:
            _, created = ProposalTemplate.objects.get_or_create(
                owner=user,
                name=name,
                defaults={
                    "body": body,
                    "placeholders": ["client", "project", "amount", "date"],
                },
            )
            if created:
                templates_created += 1

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write("  user:      demo@propotrack.test / demo1234")
        self.stdout.write(f"  clients:   {len(clients)}")
        self.stdout.write(f"  proposals: {proposals_created}")
        self.stdout.write(f"  followups: {followups_created}")
        self.stdout.write(f"  time entries: {time_entries_created}")
        self.stdout.write(f"  retainers: {retainers_created}")
        self.stdout.write(f"  templates: {templates_created}")
