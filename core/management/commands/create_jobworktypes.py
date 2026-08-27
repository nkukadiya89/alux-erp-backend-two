from django.core.management.base import BaseCommand

from common.models import JobWorkType


class Command(BaseCommand):
    help = "Initial setup: creates default JobWorkType entries."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing JobWorkTypes before creating new ones.",
        )

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing JobWorkType data...")

        if kwargs.get("reset"):
            JobWorkType.objects.all().delete()
            self.stdout.write(self.style.WARNING("All existing JobWorkTypes deleted."))

        jobwork_names = [
            "Mill Finish",
            "Engineering",
            "Surface treatment",
            "Out Source",
            "Laser marking",
            "Thermal Break",
        ]

        for name in jobwork_names:
            obj, created = JobWorkType.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {name}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Already exists: {name}"))

        self.stdout.write(self.style.SUCCESS("JobWorkType initialization complete!"))
