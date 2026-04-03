import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import Context, Template
from django.views.decorators.csrf import csrf_exempt

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericUpgrade,
)

from .api.selectors import global_search
from .forms import (
    CollectionTypeForm,
    DynamicCollectionItemForm,
    GenericServiceRecordForm,
    GenericUpgradeForm,
)
from .services.collection_services import get_collection_services
from .skills.theme_generator import CollectionThemeGenerator
from .tasks import (
    task_collection_item_enrich,
    task_collection_item_refresh_valuation,
)

logger = logging.getLogger(__name__)


# ── Legacy permalink redirects ────────────────────────────────────────────────
# These handle bookmarked or externally-linked /garage/<id>/ and
# /timepieces/<id>/ URLs.  If the legacy item was migrated to a
# DynamicCollectionItem (identified by source_vehicle_id / source_timepiece_id
# in custom_fields), we redirect transparently.  If not yet migrated, we
# return a 404 rather than serving a broken legacy view.


@login_required
def legacy_vehicle_detail_redirect(
    request: HttpRequest, vehicle_id: int
) -> HttpResponse:
    """Redirect /garage/<vehicle_id>/ to the corresponding collection item."""
    item = DynamicCollectionItem.objects.filter(
        owner=request.user,
        collection_type__slug="automobiles",
        custom_fields__source_vehicle_id=vehicle_id,
    ).first()
    if item is None:
        from django.http import Http404
        raise Http404(f"Vehicle {vehicle_id} has not been migrated to a collection item yet.")
    return redirect(
        "collections:collection_item_detail",
        collection_slug="automobiles",
        item_id=item.id,
    )


@login_required
def legacy_timepiece_detail_redirect(
    request: HttpRequest, timepiece_id: int
) -> HttpResponse:
    """Redirect /timepieces/<timepiece_id>/ to the corresponding collection item."""
    item = DynamicCollectionItem.objects.filter(
        owner=request.user,
        collection_type__slug="horology-salon",
        custom_fields__source_timepiece_id=timepiece_id,
    ).first()
    if item is None:
        from django.http import Http404
        raise Http404(f"Timepiece {timepiece_id} has not been migrated to a collection item yet.")
    return redirect(
        "collections:collection_item_detail",
        collection_slug="horology-salon",
        item_id=item.id,
    )



# ============================================================================
# DYNAMIC COLLECTION SYSTEM VIEWS
# ============================================================================


@login_required
def collection_type_list(request: HttpRequest) -> HttpResponse:
    """
    List all collection types for the user with summary stats.
    """
    collection_types = CollectionType.objects.filter(owner=request.user, is_active=True)

    # Get counts and values for each type
    type_data = []
    for ctype in collection_types:
        items = DynamicCollectionItem.objects.filter(
            collection_type=ctype, owner=request.user
        )

        count = items.count()
        total_value = sum(item.current_market_value or 0 for item in items)

        type_data.append({"type": ctype, "count": count, "total_value": total_value})

    return render(request, "my_garage/collection_types.html", {"type_data": type_data})


@login_required
def generate_collection_schema(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to generate a collection schema based on a topic string.
    Uses the Gemini-powered CollectionThemeGenerator skill.
    """
    topic = request.GET.get("topic", "").strip()
    description = request.GET.get("description", "").strip()

    logger.info(f"Generating schema for topic: '{topic}'")

    if not topic:
        logger.warning("No topic provided for schema generation")
        return JsonResponse({"error": "No topic provided."}, status=400)

    try:
        # Execute the skill
        generator = CollectionThemeGenerator()
        logger.info(
            f"CollectionThemeGenerator initialized. Enabled: {generator.enabled}"
        )

        schema = generator.generate_schema(topic, description)
        logger.info(f"Schema generated successfully: {schema}")

        return JsonResponse({"success": True, "topic": topic, "schema": schema})
    except Exception as e:
        logger.error(f"Error generating theme for topic '{topic}': {e}", exc_info=True)
        return JsonResponse(
            {"error": f"Failed to generate theme: {str(e)}"}, status=500
        )


@login_required
def generate_collection_ui(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to generate a UI component based on a topic string.
    Uses the Gemini-powered CollectionThemeGenerator skill.
    """
    topic = request.GET.get("topic", "").strip()
    description = request.GET.get("description", "").strip()
    feedback = request.GET.get("feedback", "").strip()

    logger.info(f"Generating UI for topic: '{topic}' with feedback: '{feedback}'")

    if not topic:
        return JsonResponse({"error": "No topic provided."}, status=400)

    try:
        generator = CollectionThemeGenerator()
        ui_html = generator.generate_ui_component(topic, description, feedback)

        return JsonResponse({"success": True, "topic": topic, "ui_html": ui_html})
    except Exception as e:
        logger.error(f"Error generating UI for topic '{topic}': {e}", exc_info=True)
        return JsonResponse({"error": f"Failed to generate UI: {str(e)}"}, status=500)


@csrf_exempt
@login_required
def preview_collection_ui(request: HttpRequest) -> HttpResponse:
    """
    Renders a preview of the generated UI theme with dummy data.
    Accepts POST request with 'ui_html' content.
    """
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    ui_html = request.POST.get("ui_html", "")

    if not ui_html:
        return HttpResponse("No UI HTML provided", status=400)

    try:
        # Create a template object from the HTML string
        template = Template(ui_html)

        # Mock photo object
        class MockPhoto:
            url = "https://via.placeholder.com/150"

        # Create dummy data for preview
        dummy_items = [
            {
                "name": "Sample Item 1",
                "current_market_value": 1500,
                "year": 1985,
                "condition": "Mint",
                "photo": MockPhoto(),
                "id": 1,
            },
            {
                "name": "Sample Item 2",
                "current_market_value": 2300,
                "year": 1992,
                "condition": "Good",
                "photo": MockPhoto(),
                "id": 2,
            },
            {
                "name": "Sample Item 3",
                "current_market_value": 850,
                "year": 2005,
                "condition": "Fair",
                "photo": MockPhoto(),
                "id": 3,
            },
        ]

        # Mock object to behave like a queryset/list
        class MockItems(list):
            def count(self):
                return len(self)

        items = MockItems(dummy_items)

        # Dummy collection type object
        class MockCollectionType:
            name = "Preview Collection"
            slug = "preview-collection"
            id = 999
            description = "This is a preview of your generated theme."
            icon = "fa-solid fa-layer-group"
            list_display_fields = ["year", "condition"]

        collection_type = MockCollectionType()

        context = Context(
            {
                "collection": {  # Some templates might use this
                    "title": collection_type.name,
                    "description": collection_type.description,
                    "total_items": 3,
                    "total_value": 4650,
                    "average_price": 1550,
                    "slug": collection_type.slug,
                    "id": collection_type.id,
                },
                "collection_type": collection_type,  # Standard variable name
                "items": items,
                "recent_items": items,
                "user": request.user,
                "request": request,
            }
        )

        # Render the generated UI fragment with the context
        rendered_ui_fragment = template.render(context)

        # Now render the full page using collection_list.html, passing the rendered fragment
        return render(
            request,
            "my_garage/collection_list.html",
            {
                "collection_type": collection_type,
                "items": items,
                "rendered_ui": rendered_ui_fragment,
                "preview_mode": True,  # Optional flag if template needs to know
            },
        )

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"Error rendering preview: {error_details}")
        return HttpResponse(
            f"Error rendering preview: {str(e)}<br><pre>{error_details}</pre>",
            status=500,
        )


@login_required
def collection_type_create(request: HttpRequest) -> HttpResponse:
    """
    Create a new collection type with schema builder.
    """
    if request.method == "POST":
        form = CollectionTypeForm(request.POST)

        # Get the schema JSON from the hidden field
        import json

        schema_json = request.POST.get("field_schema_json", "{}")
        list_display_fields = request.POST.get("list_display_fields_json", "[]")
        ui_theme_html = request.POST.get("ui_theme_html", "")

        if form.is_valid():
            collection_type = form.save(commit=False)
            collection_type.owner = request.user
            collection_type.ui_theme_html = ui_theme_html

            # Parse and save the schema
            try:
                collection_type.field_schema = json.loads(schema_json)
                collection_type.list_display_fields = json.loads(list_display_fields)
            except json.JSONDecodeError:
                messages.error(request, "Invalid schema format")
                return render(
                    request, "my_garage/collection_type_form.html", {"form": form}
                )

            collection_type.save()
            messages.success(
                request,
                f"Collection type '{collection_type.name}' created successfully!",
            )
            return redirect("collections:collection_type_list")
    else:
        form = CollectionTypeForm()

    return render(request, "my_garage/collection_type_form.html", {"form": form})


@login_required
def collection_type_edit(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Edit an existing collection type.
    """
    collection_type = get_object_or_404(CollectionType, slug=slug, owner=request.user)

    if request.method == "POST":
        form = CollectionTypeForm(request.POST, instance=collection_type)

        import json

        schema_json = request.POST.get("field_schema_json", "{}")
        list_display_fields = request.POST.get("list_display_fields_json", "[]")
        ui_theme_html = request.POST.get("ui_theme_html", "")

        if form.is_valid():
            collection_type = form.save(commit=False)
            collection_type.ui_theme_html = ui_theme_html

            try:
                # Handle potential empty strings or invalid JSON
                if not schema_json or schema_json == '""':
                    schema_json = "{}"
                if not list_display_fields or list_display_fields == '""':
                    list_display_fields = "[]"

                collection_type.field_schema = json.loads(schema_json)
                collection_type.list_display_fields = json.loads(list_display_fields)
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}")
                messages.error(request, "Invalid schema format")
                return render(
                    request,
                    "my_garage/collection_type_form.html",
                    {"form": form, "collection_type": collection_type},
                )

            collection_type.save()
            messages.success(
                request,
                f"Collection type '{collection_type.name}' updated successfully!",
            )
            return redirect("collections:collection_type_list")
    else:
        form = CollectionTypeForm(instance=collection_type)

    return render(
        request,
        "my_garage/collection_type_form.html",
        {"form": form, "collection_type": collection_type},
    )


@login_required
def collection_list(request: HttpRequest, collection_slug: str) -> HttpResponse:
    """
    List items in a specific collection.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )

    items = DynamicCollectionItem.objects.filter(
        collection_type=collection_type, owner=request.user
    ).order_by("-created_at")

    rendered_ui = None

    # If a custom UI theme is defined, render it as a Django template
    if collection_type.ui_theme_html:
        try:
            # Create a template object from the stored HTML string
            template = Template(collection_type.ui_theme_html)

            # Prepare context for the template
            # We need to calculate some stats if the template uses them
            total_value = sum(item.current_market_value or 0 for item in items)
            avg_price = total_value / items.count() if items.count() > 0 else 0

            context = Context(
                {
                    "collection": {
                        "title": collection_type.name,
                        "description": collection_type.description,
                        "total_items": items.count(),
                        "total_value": total_value,
                        "average_price": avg_price,
                    },
                    "items": items,
                    "recent_items": items[
                        :5
                    ],  # Just in case template uses 'recent_items'
                    "collection_type": collection_type,  # Pass the object itself too
                    "request": request,  # Pass request for URLs etc
                    "user": request.user,
                }
            )

            rendered_ui = template.render(context)
        except Exception as e:
            logger.error(
                f"Error rendering custom theme for {collection_type.name}: {e}"
            )
            # Fallback to default view if rendering fails
            messages.error(
                request, "Error rendering custom theme. Falling back to default view."
            )

    return render(
        request,
        "my_garage/collection_list.html",
        {
            "collection_type": collection_type,
            "items": items,
            "rendered_ui": rendered_ui,
        },
    )


@login_required
def collection_item_add(request: HttpRequest, collection_slug: str) -> HttpResponse:
    """
    Add a new item to a collection.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )

    if request.method == "POST":
        form = DynamicCollectionItemForm(
            request.POST, request.FILES, collection_type=collection_type
        )
        if form.is_valid():
            item = form.save(commit=False)
            item.collection_type = collection_type
            item.owner = request.user
            item.save()
            messages.success(request, f"'{item.name}' added to {collection_type.name}!")
            return redirect(
                "collections:collection_list", collection_slug=collection_slug
            )
    else:
        form = DynamicCollectionItemForm(collection_type=collection_type)

    return render(
        request,
        "my_garage/collection_item_form.html",
        {"form": form, "collection_type": collection_type},
    )


@login_required
def collection_item_detail(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """
    View and edit a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )

    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    # Get related records
    service_records = item.service_records.all()
    upgrades = item.upgrades.all()
    attachments = item.attachments.all()

    # Get relationships
    relationships_from = item.relationships_from.all()
    relationships_to = item.relationships_to.all()

    if request.method == "POST":
        form = DynamicCollectionItemForm(
            request.POST, request.FILES, instance=item, collection_type=collection_type
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"'{item.name}' updated successfully!")
            return redirect(
                "collections:collection_item_detail",
                collection_slug=collection_slug,
                item_id=item.id,
            )
    else:
        form = DynamicCollectionItemForm(instance=item, collection_type=collection_type)

    # Inject provider-specific context (buttons, winder_items, valuation_history, etc.)
    provider = get_collection_services(collection_type.service_provider_key)
    provider_context = provider.get_detail_context(item)

    # Build set of form field names that are system-managed and must not be rendered
    # as editable inputs. Catches both "system": true flag and "system_json" type,
    # regardless of how the DB schema was seeded.
    system_field_names = {
        f'custom_{field["name"]}'
        for field in collection_type.field_schema.get("fields", [])
        if field.get("system") or field.get("type") == "system_json"
    }

    return render(
        request,
        "my_garage/collection_item_detail.html",
        {
            "collection_type": collection_type,
            "item": item,
            "form": form,
            "service_records": service_records,
            "upgrades": upgrades,
            "attachments": attachments,
            "relationships_from": relationships_from,
            "relationships_to": relationships_to,
            "system_field_names": system_field_names,
            **provider_context,
        },
    )


@login_required
def collection_item_delete(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """
    Delete a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )

    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"'{item_name}' deleted successfully!")
        return redirect("collections:collection_list", collection_slug=collection_slug)

    return render(
        request,
        "my_garage/collection_item_confirm_delete.html",
        {"collection_type": collection_type, "item": item},
    )


@login_required
def collection_item_trigger_valuation(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """
    POST-only: queue a valuation refresh for a collection item.
    """
    if request.method != "POST":
        return redirect(
            "collections:collection_item_detail",
            collection_slug=collection_slug,
            item_id=item_id,
        )

    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    provider = get_collection_services(collection_type.service_provider_key)
    if provider.supports_valuation_refresh():
        task_collection_item_refresh_valuation.delay(item.id)
        messages.success(request, "Valuation refresh queued — check back shortly.")
    else:
        messages.warning(request, "Valuation refresh is not supported for this collection type.")

    return redirect(
        "collections:collection_item_detail",
        collection_slug=collection_slug,
        item_id=item_id,
    )


@login_required
def collection_item_trigger_enrich(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """
    POST-only: queue an enrichment (e.g. VIN decode) for a collection item.
    """
    if request.method != "POST":
        return redirect(
            "collections:collection_item_detail",
            collection_slug=collection_slug,
            item_id=item_id,
        )

    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    provider = get_collection_services(collection_type.service_provider_key)
    if provider.supports_enrichment():
        task_collection_item_enrich.delay(item.id)
        messages.success(request, "Enrichment queued — check back shortly.")
    else:
        messages.warning(request, "Enrichment is not supported for this collection type.")

    return redirect(
        "collections:collection_item_detail",
        collection_slug=collection_slug,
        item_id=item_id,
    )


@login_required
def all_services_view(request: HttpRequest) -> HttpResponse:
    """
    View all service records across ALL collections.
    """
    # Get all service records for user's collection items
    service_records = (
        GenericServiceRecord.objects.filter(item__owner=request.user)
        .select_related("item", "item__collection_type")
        .order_by("-date")
    )

    return render(
        request, "my_garage/all_services.html", {"service_records": service_records}
    )


@login_required
def all_upgrades_view(request: HttpRequest) -> HttpResponse:
    """
    View all upgrades across ALL collections.
    """
    # Get all upgrades for user's collection items
    upgrades = (
        GenericUpgrade.objects.filter(item__owner=request.user)
        .select_related("item", "item__collection_type")
        .order_by("-completion_date", "-ordered_date")
    )

    return render(request, "my_garage/all_upgrades.html", {"upgrades": upgrades})


@login_required
def collection_item_add_service(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """
    Add a service record to a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    if request.method == "POST":
        form = GenericServiceRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.item = item
            record.is_verified = True  # Manually added records are verified by default
            record.save()

            messages.success(request, "Service record added successfully.")
            return redirect(
                "collections:collection_item_detail",
                collection_slug=collection_slug,
                item_id=item.id,
            )
    else:
        form = GenericServiceRecordForm()

    return render(
        request,
        "my_garage/collection_service_record_form.html",
        {
            "form": form,
            "item": item,
            "collection_type": collection_type,
            "title": "Add Service Record",
        },
    )


@login_required
def collection_item_edit_service(
    request: HttpRequest, collection_slug: str, item_id: int, record_id: int
) -> HttpResponse:
    """
    Edit a service record for a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )
    record = get_object_or_404(GenericServiceRecord, pk=record_id, item=item)

    if request.method == "POST":
        form = GenericServiceRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Service record updated.")
            return redirect(
                "collections:collection_item_detail",
                collection_slug=collection_slug,
                item_id=item.id,
            )
    else:
        form = GenericServiceRecordForm(instance=record)

    return render(
        request,
        "my_garage/collection_service_record_form.html",
        {
            "form": form,
            "item": item,
            "collection_type": collection_type,
            "title": "Edit Service Record",
            "is_edit": True,
            "record": record,
        },
    )


@login_required
def collection_item_delete_service(
    request: HttpRequest, collection_slug: str, item_id: int, record_id: int
) -> HttpResponse:
    """
    Delete a service record from a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )
    record = get_object_or_404(GenericServiceRecord, pk=record_id, item=item)

    if request.method == "POST":
        record.delete()
        messages.success(request, "Service record deleted.")
        return redirect(
            "collections:collection_item_detail",
            collection_slug=collection_slug,
            item_id=item.id,
        )

    return render(
        request,
        "my_garage/confirm_delete.html",
        {
            "object": record,
            "type": "Service Record",
            "cancel_url": f"/garage/collections/{collection_slug}/items/{item_id}/",
        },
    )


@login_required
def collection_item_add_upgrade(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """
    Add an upgrade/modification project to a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    if request.method == "POST":
        form = GenericUpgradeForm(request.POST)
        if form.is_valid():
            upgrade = form.save(commit=False)
            upgrade.item = item
            upgrade.save()

            messages.success(request, f"Project '{upgrade.name}' started!")
            return redirect(
                "collections:collection_item_detail",
                collection_slug=collection_slug,
                item_id=item.id,
            )
    else:
        form = GenericUpgradeForm()

    return render(
        request,
        "my_garage/upgrade_form.html",
        {
            "form": form,
            "vehicle": item,
            "title": "Start New Project",
            "is_collection": True,
            "collection_slug": collection_slug,
        },
    )


@login_required
def collection_item_edit_upgrade(
    request: HttpRequest, collection_slug: str, item_id: int, upgrade_id: int
) -> HttpResponse:
    """
    Edit an upgrade/modification project.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )
    upgrade = get_object_or_404(GenericUpgrade, pk=upgrade_id, item=item)

    if request.method == "POST":
        form = GenericUpgradeForm(request.POST, instance=upgrade)
        if form.is_valid():
            form.save()
            messages.success(request, f"Project '{upgrade.name}' updated.")
            return redirect(
                "collections:collection_item_detail",
                collection_slug=collection_slug,
                item_id=item.id,
            )
    else:
        form = GenericUpgradeForm(instance=upgrade)

    return render(
        request,
        "my_garage/upgrade_form.html",
        {
            "form": form,
            "vehicle": item,
            "title": "Edit Project",
            "is_edit": True,
            "upgrade": upgrade,
            "is_collection": True,
            "collection_slug": collection_slug,
        },
    )


@login_required
def collection_item_delete_upgrade(
    request: HttpRequest, collection_slug: str, item_id: int, upgrade_id: int
) -> HttpResponse:
    """
    Delete an upgrade/modification project.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )
    upgrade = get_object_or_404(GenericUpgrade, pk=upgrade_id, item=item)

    if request.method == "POST":
        upgrade.delete()
        messages.success(request, f"Project '{upgrade.name}' deleted.")
        return redirect(
            "collections:collection_item_detail",
            collection_slug=collection_slug,
            item_id=item.id,
        )

    return render(
        request,
        "my_garage/confirm_delete.html",
        {
            "object": upgrade,
            "type": "Upgrade Project",
            "cancel_url": f"/garage/collections/{collection_slug}/items/{item_id}/",
        },
    )


@login_required
def collection_upgrades_kanban(
    request: HttpRequest, collection_slug: str
) -> HttpResponse:
    """
    Kanban board view for all upgrades in a collection.
    """
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )

    # Get all upgrades for this collection, grouped by status
    items = DynamicCollectionItem.objects.filter(
        collection_type=collection_type, owner=request.user
    )

    upgrades = (
        GenericUpgrade.objects.filter(item__in=items)
        .select_related("item")
        .order_by("status", "-ordered_date", "-completion_date")
    )

    # Group upgrades by status
    wishlist = upgrades.filter(status="WISHLIST")
    ordered = upgrades.filter(status="ORDERED")
    in_progress = upgrades.filter(status="IN_PROGRESS")
    completed = upgrades.filter(status="COMPLETED")
    cancelled = upgrades.filter(status="CANCELLED")

    return render(
        request,
        "my_garage/collection_upgrades_kanban.html",
        {
            "collection_type": collection_type,
            "wishlist": wishlist,
            "ordered": ordered,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
        },
    )


@login_required
def collection_upgrade_update_status(
    request: HttpRequest, upgrade_id: int
) -> HttpResponse:
    """
    AJAX endpoint to update upgrade status (for kanban drag-and-drop).
    """
    import json

    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    upgrade = get_object_or_404(GenericUpgrade, pk=upgrade_id, item__owner=request.user)

    try:
        data = json.loads(request.body)
        new_status = data.get("status")

        if new_status not in dict(GenericUpgrade.STATUS_CHOICES):
            return JsonResponse({"error": "Invalid status"}, status=400)

        upgrade.status = new_status

        # Update dates based on status
        if new_status == "COMPLETED" and not upgrade.completion_date:
            from django.utils import timezone

            upgrade.completion_date = timezone.now().date()
        elif new_status == "ORDERED" and not upgrade.ordered_date:
            from django.utils import timezone

            upgrade.ordered_date = timezone.now().date()

        upgrade.save()

        return JsonResponse(
            {
                "success": True,
                "status": new_status,
                "status_display": upgrade.get_status_display(),
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def global_search_view(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint for global search.
    """
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

    results = global_search(request.user, query)
    return JsonResponse({"results": results})


def button_test_view(request: HttpRequest) -> HttpResponse:
    """
    Debug view to test button functionality (no login required for testing).
    """
    return render(request, "my_garage/button_test.html", {})


