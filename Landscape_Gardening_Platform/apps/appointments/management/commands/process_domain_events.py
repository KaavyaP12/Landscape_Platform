import time
from django.core.management.base import BaseCommand
from apps.appointments.event_processor import process_pending_events


class Command(BaseCommand):
    help = "Process pending domain events for appointment workflow"

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Keep polling for events")
        parser.add_argument("--sleep", type=int, default=3, help="Sleep seconds between loops")
        parser.add_argument("--batch-size", type=int, default=20, help="Max events per cycle")

    def handle(self, *args, **options):
        loop = options["loop"]
        sleep_seconds = options["sleep"]
        batch_size = options["batch_size"]

        if not loop:
            count = process_pending_events(batch_size=batch_size)
            self.stdout.write(self.style.SUCCESS(f"Processed {count} event(s)"))
            return

        self.stdout.write(self.style.SUCCESS("Starting event worker..."))
        while True:
            count = process_pending_events(batch_size=batch_size)
            if count:
                self.stdout.write(self.style.SUCCESS(f"Processed {count} event(s)"))
            time.sleep(sleep_seconds)