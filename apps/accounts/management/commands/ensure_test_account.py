import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create or update a full-access test account."

    def handle(self, *args, **opts):
        email = os.getenv("TEST_ACCOUNT_EMAIL", "test@bakemastererp.com")
        password = os.getenv("TEST_ACCOUNT_PASSWORD", "Test@2026ERP!")
        modules = [module for module, _label in User.MODULES]

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "full_name": os.getenv("TEST_ACCOUNT_NAME", "ERP Test Admin"),
                "employee_code": os.getenv("TEST_ACCOUNT_CODE", "TEST-ADMIN-001"),
                "role": User.Role.ADMINISTRATOR,
                "department": "Testing",
                "can_access_all_locations": True,
                "allowed_modules": modules,
                "can_override_negative_stock": True,
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} test account: {email}"))
