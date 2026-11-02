from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from my_garage.management.commands.seed_tutorial_demo import (
    DEMO_PASSWORD,
    DEMO_USERNAME,
)
from my_garage.models import CollectionType

User = get_user_model()


@pytest.fixture(autouse=True)
def _tutorials_settings(settings):
    settings.SETTINGS_MODULE = "config.settings.tutorials"


@pytest.mark.django_db
def test_creates_demo_user_with_no_collections():
    call_command("seed_tutorial_demo")
    user = User.objects.get(username=DEMO_USERNAME)
    assert user.check_password(DEMO_PASSWORD)
    assert not CollectionType.objects.filter(owner=user).exists()


@pytest.mark.django_db
def test_is_idempotent_and_resets_password():
    call_command("seed_tutorial_demo")
    user = User.objects.get(username=DEMO_USERNAME)
    user.set_password("changed")
    user.save()
    call_command("seed_tutorial_demo")
    assert User.objects.filter(username=DEMO_USERNAME).count() == 1
    assert User.objects.get(username=DEMO_USERNAME).check_password(DEMO_PASSWORD)


@pytest.mark.django_db
def test_refuses_outside_tutorials_settings(settings):
    settings.SETTINGS_MODULE = "config.settings.test"
    with pytest.raises(CommandError, match="only runs under"):
        call_command("seed_tutorial_demo")
    assert not User.objects.filter(username=DEMO_USERNAME).exists()
