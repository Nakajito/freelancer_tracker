from datetime import date

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import translation
from django.utils.formats import date_format

from apps.accounts.models import User
from apps.exports.services import MonthlySummaryGenerator


class Command(BaseCommand):
    help = "Send daily digest with overdue follow-ups"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Don't send emails")

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)

        for user in users:
            self.send_digest(user, options["dry_run"])

    def send_digest(self, user, dry_run):
        from apps.followups.services import FollowUpQuerySet

        overdue = FollowUpQuerySet.overdue(user)
        upcoming = FollowUpQuerySet.upcoming(user, days=7)

        if not overdue and not upcoming:
            return

        today = date.today()
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1)
        period_label = date_format(today, "F Y")
        month_summary = MonthlySummaryGenerator.generate(
            user,
            start_date,
            end_date,
            period_label,
        )

        context = {
            "user": user,
            "overdue": overdue,
            "upcoming": upcoming,
            "month_summary": month_summary,
        }

        lang = getattr(user, "language_preference", "en") or "en"
        with translation.override(lang):
            message = render_to_string("partials/digest_email.txt", context)
            subject = f"Digest - {today.strftime('%Y-%m-%d')}"

        if not dry_run:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            self.stdout.write(self.style.SUCCESS(f"Sent digest to {user.email}"))
        else:
            self.stdout.write(f"Would send digest to {user.email}")
