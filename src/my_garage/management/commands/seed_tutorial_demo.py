"""
Management command: seed_tutorial_demo

Creates the fixed demo user the tutorial recorder signs in as. The user starts
with no collections, so the recording shows a genuine first-time vault.
Idempotent: re-running resets the password and leaves everything else alone.

Usage:
    pixi run manage seed_tutorial_demo
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "tutorial-demo-pass"
ALLOWED_SETTINGS = "config.settings.tutorials"


class Command(BaseCommand):
    help = "Create the fixed demo user used by `pixi run record-tutorials`."

    def handle(self, *args, **options):
        # The password is in the repo, so never create this user anywhere real.
        if settings.SETTINGS_MODULE != ALLOWED_SETTINGS:
            raise CommandError(
                f"seed_tutorial_demo only runs under {ALLOWED_SETTINGS} "
                f"(current: {settings.SETTINGS_MODULE})."
            )
        User = get_user_model()
        user, created = User.objects.get_or_create(username=DEMO_USERNAME)
        user.set_password(DEMO_PASSWORD)
        user.save()
        self.stdout.write(
            f"{'Created' if created else 'Updated'} demo user '{DEMO_USERNAME}'."
        )
