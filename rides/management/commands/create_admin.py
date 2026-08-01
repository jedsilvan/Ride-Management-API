from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from rides.models import Profile


class Command(BaseCommand):
    help = "Give an existing auth user an admin-role Profile, so they can call the API."

    def add_arguments(self, parser):
        parser.add_argument(
            "username", help="Username of an existing user (e.g. one made with createsuperuser)"
        )

    def handle(self, *args, **options):
        username = options["username"]
        auth_user_model = get_user_model()

        try:
            user = auth_user_model.objects.get(username=username)
        except auth_user_model.DoesNotExist as exc:
            raise CommandError(
                f"No user named '{username}'. Run 'python manage.py createsuperuser' first."
            ) from exc

        profile, created = Profile.objects.get_or_create(
            user=user, defaults={"role": "admin"}
        )
        if not created and profile.role != "admin":
            profile.role = "admin"
            profile.save()

        self.stdout.write(self.style.SUCCESS(f"'{username}' now has role='admin'."))
