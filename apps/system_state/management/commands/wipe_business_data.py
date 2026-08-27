from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Disabled: this project does not allow command-line data wipes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true",
            help="Accepted for backward compatibility; the command is always blocked.",
        )

    def handle(self, *args, **options):
        raise CommandError("wipe_business_data is disabled to protect ERP data.")
