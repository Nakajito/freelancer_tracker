import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus, Tag
from apps.followups.models import FollowUp


class Command(BaseCommand):
    help = "Seeds the database with demo data"

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            email="demo@example.com",
            defaults={"username": "demo", "first_name": "Demo", "last_name": "User"},
        )
        user.set_password("demo123456")
        user.save()

        client1, _ = Client.objects.get_or_create(
            owner=user,
            name="Acme Corp",
            defaults={"email": "contact@acme.com", "notes": "Big client"},
        )

        client2, _ = Client.objects.get_or_create(
            owner=user,
            name="Tech Startup Inc",
            defaults={"email": "hello@techstartup.io"},
        )

        tag1, _ = Tag.objects.get_or_create(
            owner=user, slug="django", defaults={"name": "Django"}
        )
        tag2, _ = Tag.objects.get_or_create(
            owner=user, slug="react", defaults={"name": "React"}
        )
        tag3, _ = Tag.objects.get_or_create(
            owner=user, slug="urgent", defaults={"name": "Urgent"}
        )

        statuses = [
            ProposalStatus.DRAFT,
            ProposalStatus.SENT,
            ProposalStatus.VIEWED,
            ProposalStatus.RESPONDED,
            ProposalStatus.NEGOTIATING,
            ProposalStatus.ACCEPTED,
            ProposalStatus.REJECTED,
        ]

        platforms = [p[0] for p in Platform.choices]

        for i in range(15):
            sent_date = date.today() - timedelta(days=random.randint(1, 90))
            status = random.choice(statuses)

            proposal = Proposal.objects.create(
                owner=user,
                title=f"Project {i + 1} - {random.choice(['Web App', 'API', 'Landing Page', 'Dashboard'])}",
                platform=random.choice(platforms),
                client=random.choice([client1, client2]),
                proposal_text=f"Proposal for project {i + 1}. Looking to deliver high quality work.",
                amount=random.randint(500, 10000),
                status=status,
                sent_date=sent_date,
                expected_response_date=sent_date + timedelta(days=7),
            )

            proposal.tags.add(random.choice([tag1, tag2, tag3]))

            if status in [
                ProposalStatus.RESPONDED,
                ProposalStatus.NEGOTIATING,
                ProposalStatus.ACCEPTED,
                ProposalStatus.REJECTED,
            ]:
                proposal.actual_response_date = sent_date + timedelta(
                    days=random.randint(1, 7)
                )
                proposal.save()

            if (
                status in [ProposalStatus.SENT, ProposalStatus.VIEWED]
                and random.random() > 0.5
            ):
                FollowUp.objects.create(
                    proposal=proposal,
                    description=f"Follow up on proposal for {proposal.title}",
                    due_date=date.today() + timedelta(days=random.randint(-5, 5)),
                )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
