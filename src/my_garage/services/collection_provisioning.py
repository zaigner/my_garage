"""
Collection provisioning — turn catalogue blueprints into a user's collections.

This is the write path behind the onboarding picker.  A user selects blueprint
slugs, and each one becomes a fully-formed CollectionType owned by them: schema,
list display, icon, service provider, and custom theme all populated up front.
No AI generation, no schema editing, no follow-up input screens.

    from my_garage.services.collection_provisioning import provision_collections

    created = provision_collections(request.user, ["automobiles", "wine-collection"])

Idempotency
-----------
Provisioning keys on ``(owner, slug)``.  Re-running with the same slugs creates
nothing and returns an empty list.  A collection the user already owns at that
slug is never modified — including one they built themselves — so this is safe
to call repeatedly and safe to expose as an "add more" action.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from my_garage.collection_blueprints import (
    list_blueprints,
    load_ui_theme,
)
from my_garage.models import CollectionType


def provision_collections(
    user: AbstractBaseUser, slugs: list[str]
) -> list[CollectionType]:
    """
    Create the catalogue collections named in *slugs* for *user*.

    Unknown slugs are ignored rather than raising — the slug list arrives from a
    form POST and must not be trusted to match the catalogue.

    Returns the CollectionType rows that were newly created, in catalogue order.
    """
    requested = set(slugs or [])
    if not requested:
        return []

    created: list[CollectionType] = []

    with transaction.atomic():
        # Iterate the catalogue (not the request) so ordering is deterministic
        # and unknown slugs fall away naturally.
        for blueprint in list_blueprints():
            slug = blueprint["slug"]
            if slug not in requested:
                continue

            # Never clobber an existing collection at this slug, whether it came
            # from an earlier provision or the user built it themselves.
            if CollectionType.objects.filter(owner=user, slug=slug).exists():
                continue

            ctype = CollectionType(
                owner=user,
                slug=slug,
                name=blueprint["name"],
                icon=blueprint["icon"],
                description=blueprint["description"],
                field_schema=blueprint["field_schema"],
                list_display_fields=blueprint["list_display_fields"],
                service_provider_key=blueprint["service_provider_key"],
                is_system=blueprint.get("is_system", False),
                ui_theme_html=load_ui_theme(blueprint),
            )
            ctype.save()
            created.append(ctype)

    return created


def get_catalog(user: AbstractBaseUser) -> list[dict]:
    """
    Return the blueprint catalogue annotated for display to *user*.

    Each entry gains:
      ``already_owned``  True when the user already has a collection at this slug
      ``field_count``    number of user-editable fields (system fields excluded)

    Heavy schema keys are dropped — templates only need the display metadata.
    """
    owned_slugs = set(
        CollectionType.objects.filter(owner=user).values_list("slug", flat=True)
    )

    catalog = []
    for blueprint in list_blueprints():
        fields = blueprint["field_schema"].get("fields", [])
        visible_fields = [
            f for f in fields if not (f.get("system") or f.get("type") == "system_json")
        ]
        catalog.append(
            {
                "slug": blueprint["slug"],
                "name": blueprint["name"],
                "icon": blueprint["icon"],
                "description": blueprint["description"],
                "preview": blueprint.get("preview", ""),
                "is_system": blueprint.get("is_system", False),
                "already_owned": blueprint["slug"] in owned_slugs,
                "field_count": len(visible_fields),
            }
        )
    return catalog
