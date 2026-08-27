from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Disabled: this project does not allow command-line user deletion."

    def add_arguments(self, parser):
        parser.add_argument("--keep-user", required=True, help="Email of the user to keep.")
        parser.add_argument(
            "--yes", action="store_true",
            help="Accepted for backward compatibility; the command is always blocked.",
        )

    def handle(self, *args, **options):
        raise CommandError("delete_other_users is disabled to protect ERP user data.")
