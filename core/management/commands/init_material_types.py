from django.core.management.base import BaseCommand

from melting_furnace.models import MaterialType

SEED_DATA = [
    ("BAIL", "Bailing", "Primary aluminum bailing"),
    ("SCRP", "Scrap", "Clean process scrap"),
    ("MIXS", "Mixed Scrap", "Scrap mix from returns"),
    ("ING", "Ingot", "Primary ingot"),
    ("CONT", "Contaminated Scrap", "Heavy scrap"),
    ("ALUM", "Aluminum", "Aluminum metal"),
]


class Command(BaseCommand):
    help = "Initialize MaterialType master data (idempotent)."

    def handle(self, *args, **options):
        created = 0
        for code, name, description in SEED_DATA:
            _, was_created = MaterialType.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": description, "is_active": True},
            )
            if was_created:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created MaterialType: {code} - {name}")
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"MaterialType init complete. Created: {created}, existing: {len(SEED_DATA) - created}"
            )
        )
