from datetime import date

from django.core.management.base import BaseCommand

from apps.timetracking.models import RecurringRetainer
from apps.timetracking.services import RetainerGeneratorService


class Command(BaseCommand):
    help = "Generate time entries for recurring retainers"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=date.today().year)
        parser.add_argument("--month", type=int, default=date.today().month)

    def handle(self, *args, **options):
        year = options["year"]
        month = options["month"]

        retainers = RecurringRetainer.objects.filter(active=True)

        total_generated = 0
        for retainer in retainers:
            entries = RetainerGeneratorService.generate_entries(retainer, year, month)
            total_generated += len(entries)
            if entries:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Generated {len(entries)} entries for {retainer.proposal.title}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"Total entries generated: {total_generated}")
        )
